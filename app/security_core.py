"""
security_core.py
────────────────────────────────────────────────────────────────────────────
[팀원 B] 오토코어 AI 보안 게이트웨이 - 순수 파이썬 보안 엔진

담당: 팀원 B (보안 코어)
연동 예정: 팀원 C의 FastAPI /chat 엔드포인트에서 이 모듈을 import하여 사용

의존성: 표준 라이브러리(re, secrets)만 사용 — 외부 프레임워크 없음
────────────────────────────────────────────────────────────────────────────
"""

import re
import secrets

# ── 타입 별칭 (가독성) ───────────────────────────────────────────────────────
MaskedText  = str
MappingDict = dict[str, str]   # {"[BLUEPRINT_a1b2c3]": "DWG-2026-X1", ...}


# ══════════════════════════════════════════════════════════════════════════════
#  기능 1: 프롬프트 인젝션 탐지 (check_intent)
# ══════════════════════════════════════════════════════════════════════════════

# 악의적 키워드 패턴 목록: (정규식 패턴, 차단 사유)
# ※ 추후 PromptGuard / HuggingFace 분류 모델로 교체 시
#   이 함수의 시그니처(입/출력)를 유지한 채 내부 로직만 교체하면 됨.
_INJECTION_PATTERNS: list[tuple[str, str]] = [
    # ── 한국어 공격 패턴 ──────────────────────────────────────────────────
    (r"무시\s*하고",                             "시스템 명령 무력화 시도 (한국어)"),
    (r"이전\s*(지시|명령|프롬프트).*무시",         "이전 지시 무력화 시도"),
    (r"시스템\s*프롬프트",                         "시스템 프롬프트 접근 시도"),
    (r"비밀번호\s*알려\s*줘",                      "비밀번호 탈취 시도"),
    (r"탈옥",                                     "탈옥(Jailbreak) 시도"),
    (r"관리자\s*권한",                             "권한 상승 시도"),
    (r"내부\s*(시스템|규칙|설정).*알려",            "내부 시스템 정보 탈취 시도"),
    (r"역할.*바꿔",                               "역할 변조 시도 (한국어)"),

    # ── 영문 공격 패턴 ────────────────────────────────────────────────────
    (r"ignore\s+(?:(?:previous|all|your)\s+)*instructions?", "명령 무력화 시도 (영문)"),
    (r"disregard\s+(previous|all|your)",          "명령 무력화 시도 (영문)"),
    (r"you\s+are\s+now",                          "역할 변경 시도 (영문)"),
    (r"\bact\s+as\b",                             "역할 변경 시도 (영문)"),
    (r"pretend\s+(you\s+are|to\s+be)",            "역할 변조 시도 (영문)"),
    (r"\bDAN\b.*mode",                            "DAN 탈옥 시도"),
    (r"jailbreak",                                "탈옥(Jailbreak) 키워드 탐지"),
    (r"reveal\s+(your|the)\s+(secret|prompt|instruction)", "프롬프트 정보 탈취 시도"),
    (r"override\s+(your|the)\s+(safety|guideline)", "안전장치 우회 시도"),

    # ── [신규] 시스템/설정 파일 접근 탐지 ───────────────────────────────
    # config.json / .env / 내부 파일·디렉토리 탈취 시도
    (r"config\.json",                             "시스템 설정 파일 탈취 시도 (config.json)"),
    (r"\.env\b",                                  "환경변수 파일 탈취 시도 (.env)"),
    (r"시스템\s*(설정|파일|구성)",                  "시스템 설정 파일 접근 시도"),
    (r"내부\s*파일",                               "내부 파일 탈취 시도"),
    (r"디렉토리.*보여\s*줘|내용.*전부\s*보여",       "파일 시스템 탐색 시도"),
    (r"(설정|구성)\s*파일.*내용",                   "설정 파일 내용 탈취 시도"),

    # ── [신규] 네트워크/인프라 탐색 탐지 ────────────────────────────────
    # IP 주소, 내부망, 포트 스캔, 서버 아키텍처 정보 탈취 시도
    (r"IP\s*(주소|address)",                   "내부 IP 탈취 시도"),
    (r"내부\s*(망|네트워크|network)",              "내부망 탐색 시도"),
    (r"포트\s*스캔|port\s*scan",                   "포트 스캔 시도"),
    (r"서버\s*(아키텍처|구조|정보).*알려",           "서버 인프라 정보 탈취 시도"),
    (r"(내부|internal)\s*(endpoint|api|url)",      "내부 API 엔드포인트 탐색 시도"),

    # ── [신규] 권한 상승/명령 실행 탐지 ─────────────────────────────────
    # sudo, bash, cmd, 관리자 권한 탈취 시도
    (r"\bsudo\b",                                 "관리자 명령 실행 시도 (sudo)"),
    (r"\bbash\b|\bsh\s+-c\b",                     "쉘 명령 실행 시도 (bash/sh)"),
    (r"\bcmd\.exe\b|\bpowershell\b",              "윈도우 명령 실행 시도 (cmd/powershell)"),
    (r"관리자\s*(계정|모드|로그인)",                "관리자 계정 탈취 시도"),
    (r"root\s*(권한|access|shell)",               "루트 권한 탈취 시도"),
]


def check_intent(prompt: str) -> tuple[bool, str]:
    """
    프롬프트 인젝션 및 악의적 의도 탐지.

    Args:
        prompt: 사용자가 입력한 원본 프롬프트 문자열

    Returns:
        tuple[bool, str]:
            - (True,  "차단 사유") : 악의적 패턴 탐지 → 차단 권고
            - (False, "")         : 정상 프롬프트 → 통과

    Note:
        현재는 정규식 기반 1단계 필터.
        향후 PromptGuard / fine-tuned BERT 모델 등으로 내부 로직 교체 가능.
        함수 시그니처는 변경하지 않음으로써 팀원 C의 API 코드 수정 불필요.
    """
    for pattern, reason in _INJECTION_PATTERNS:
        if re.search(pattern, prompt, re.IGNORECASE):
            return True, reason
    return False, ""


# ══════════════════════════════════════════════════════════════════════════════
#  기능 2: 오토코어 맞춤형 NER 패턴 정의
# ══════════════════════════════════════════════════════════════════════════════

# (토큰 접두사, 정규식 패턴)
# 패턴 적용 우선순위: 리스트 순서대로 순차 검사
_SECRET_PATTERNS: list[tuple[str, str]] = [
    # 설계 도면 번호: DWG-2026-X1, DWG-2025-AB12C 등
    # 규칙: DWG- + 4자리 연도 + - + 영대문자/숫자 조합(1자 이상)
    (
        "BLUEPRINT",
        r"DWG-\d{4}-[A-Z0-9]+",
    ),

    # 정밀 치수 / 공차값: 공차 ±0.005mm, 공차 ±1.23mm 등
    # 규칙: '공차' + 공백* + ± + 공백* + 정수.소수 + 공백* + mm
    (
        "DIMENSION",
        r"공차\s*±\s*\d+\.\d+\s*mm",
    ),

    # 임직원 휴대전화: 010-1234-5678
    # 규칙: 010 + - + 4자리 + - + 4자리
    (
        "PHONE",
        r"010-\d{4}-\d{4}",
    ),
]


# ── 내부 헬퍼: 동적 난수 토큰 생성 ────────────────────────────────────────────

def _generate_token(prefix: str) -> str:
    """
    암호학적으로 안전한 난수 토큰 생성.

    Args:
        prefix: 토큰 유형 접두사 (예: "BLUEPRINT", "PHONE")

    Returns:
        str: "[PREFIX_6자리16진수]" 형태 토큰 (예: [BLUEPRINT_a1b2c3])

    Note:
        secrets.token_hex(3) → 6자리 16진수 → 16^6 ≈ 1,677만 가지 조합
        동일 텍스트라도 매번 다른 토큰이 생성됨 (동적성 보장)
    """
    rand_hex = secrets.token_hex(3)   # 예: "a1b2c3"
    return f"[{prefix}_{rand_hex}]"


# ══════════════════════════════════════════════════════════════════════════════
#  기능 3: 실시간 마스킹 (mask_data)
# ══════════════════════════════════════════════════════════════════════════════

def mask_data(text: str) -> tuple[MaskedText, MappingDict]:
    """
    입력 텍스트에서 오토코어 기밀 데이터를 동적 토큰으로 치환(마스킹).

    Args:
        text: 사용자 원본 프롬프트

    Returns:
        tuple[MaskedText, MappingDict]:
            - MaskedText  : 기밀이 [TOKEN_난수] 형태로 치환된 안전한 텍스트
                            → 이 텍스트만 외부 LLM API로 전송됨
            - MappingDict : {"[BLUEPRINT_a1b2c3]": "DWG-2026-X1", ...}
                            → Redis 인메모리에 임시 보관, unmask_data()에서 참조

    Note:
        동일 원본값이 텍스트 내 여러 번 등장하면 같은 토큰으로 일관성 있게 치환.
        re.sub + 클로저 패턴으로 O(n) 단일 패스 처리.
    """
    masked_text: str    = text
    mapping_dict: MappingDict = {}

    # 역방향 조회용: original → token (동일 원본 중복 방지)
    _original_to_token: dict[str, str] = {}

    for prefix, pattern in _SECRET_PATTERNS:
        def _replacer(match: re.Match, _prefix: str = prefix) -> str:
            original: str = match.group(0)
            if original not in _original_to_token:
                token = _generate_token(_prefix)
                _original_to_token[original] = token
                mapping_dict[token] = original
            return _original_to_token[original]

        masked_text = re.sub(pattern, _replacer, masked_text)

    return masked_text, mapping_dict


# ══════════════════════════════════════════════════════════════════════════════
#  기능 4: 원본 역치환 (unmask_data)
# ══════════════════════════════════════════════════════════════════════════════

def unmask_data(masked_text: str, mapping_dict: MappingDict) -> str:
    """
    외부 AI 응답에 포함된 동적 토큰을 원본 기밀 데이터로 역치환(복원).

    Args:
        masked_text  : 외부 LLM이 생성한 응답 텍스트 (토큰 포함)
        mapping_dict : mask_data()가 반환한 역치환 매핑 딕셔너리

    Returns:
        str: 모든 토큰이 원본 데이터로 완전히 복원된 최종 텍스트
             → 이 텍스트를 사용자(팀원 A UI)에게 최종 출력

    Note:
        매핑 딕셔너리가 비어 있으면 입력 텍스트를 그대로 반환 (안전 동작).
        AI가 토큰을 변형하거나 누락시킨 경우 해당 토큰은 복원되지 않음.
    """
    result: str = masked_text
    for token, original in mapping_dict.items():
        result = result.replace(token, original)
    return result
