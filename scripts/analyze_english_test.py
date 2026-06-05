import pandas as pd
from sqlalchemy import create_engine
import os, glob

def analyze():
    # 로컬 CSV 파일에서 로그 가져오기
    df_logs = pd.read_csv('logs.csv', encoding='utf-16')
    
    data_folder = os.path.join(os.path.dirname(os.path.abspath('tests/qa_tester/tester.py')), 'test_data')
    files = sorted(glob.glob(os.path.join(data_folder, '*.csv')))
    
    expected_data = []
    for f in files:
        try:
            df = pd.read_csv(f, encoding='utf-8-sig').dropna(subset=['original_prompt']).head(15)
        except UnicodeDecodeError:
            df = pd.read_csv(f, encoding='cp949').dropna(subset=['original_prompt']).head(15)
        phase = os.path.basename(f).split('_')[0]
        for prompt in df['original_prompt']:
            p_str = str(prompt).strip()
            if phase == 'phase1':
                expected_status = 'ALLOWED'
                expected_mask = False
            elif phase in ['phase2', 'phase3']:
                expected_status = 'ALLOWED'
                expected_mask = True
            elif phase == 'phase4':
                expected_status = 'BLOCKED'
                expected_mask = False
            expected_data.append({'prompt': p_str, 'phase': phase, 'expected_status': expected_status, 'expected_mask': expected_mask})
    
    df_expected = pd.DataFrame(expected_data)
    
    results = []
    for idx, row in df_expected.iterrows():
        match = df_logs[df_logs['original_prompt'] == row['prompt']]
        if match.empty:
            status = 'MISSING_IN_DB'
            actual_action = None
            has_mask = False
            details = ''
        else:
            m_row = match.iloc[0]
            actual_status = m_row['status']
            has_mask = pd.notna(m_row['mapping_dict']) and m_row['mapping_dict'] != '{}' and str(m_row['mapping_dict']).strip() != ''
            details = m_row['detected_threat'] if actual_status == 'BLOCKED' else m_row['mapping_dict']
            
            status = 'PASS'
            if row['expected_status'] != actual_status:
                status = 'FAIL_ACTION'
            elif row['expected_mask'] and not has_mask:
                status = 'FAIL_MASK (FN)'
            elif not row['expected_mask'] and has_mask and row['phase'] == 'phase1':
                status = 'FAIL_OVERMASK (FP)'
                
        results.append({
            'Phase': row['phase'], 
            'Status': status, 
            'Prompt': row['prompt'][:50], 
            'Details': details,
            'Expected_Status': row['expected_status'],
            'Actual_Status': actual_status,
            'Has_Mask': has_mask
        })

    df_res = pd.DataFrame(results)
    
    print("=== ENGLISH TEST RESULTS SUMMARY ===")
    if not df_res.empty:
        summary = df_res.groupby(['Phase', 'Status']).size().unstack(fill_value=0)
        print(summary)
    else:
        print("No results to display.")
        
    print("\n=== FAILED / MISSING CASES ===")
    fails = df_res[df_res['Status'] != 'PASS']
    if fails.empty:
        print("All tests passed perfectly!")
    else:
        for idx, r in fails.iterrows():
            print(f"[{r['Phase']}] {r['Status']}")
            print(f"   Prompt: {r['Prompt']}...")
            print(f"   Status: Exp={r['Expected_Status']}, Act={r['Actual_Status']}")
            print(f"   Details: {r['Details']}")
            print("-" * 40)

if __name__ == '__main__':
    analyze()
