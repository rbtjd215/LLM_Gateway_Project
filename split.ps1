Remove-Item rewrite.ps1 -ErrorAction SilentlyContinue

$rootDate = git log -1 --format="%cD" ff6da2e
$env:GIT_COMMITTER_DATE = $rootDate
$env:GIT_AUTHOR_DATE = $rootDate

git checkout --orphan temp_split
git reset

git add app
git commit -m "feat: Setup backend core logic and routers"

git add frontend
git commit -m "feat: Create frontend dashboard interface"

git add scripts
git commit -m "feat: Add operational and analysis scripts"

git add tests
git commit -m "test: Add QA test suites and security tests"

git add Docs_English Docs_Korean assets README.md README_EN.md implementation_plan.md
git commit -m "docs: Add comprehensive project documentation and assets"

git add .
git commit -m "chore: Configure project settings and Docker environments"

$commits = @("4dd3137", "4c1a35d", "39815b5", "2c0a931")
foreach ($c in $commits) {
    $cDate = git log -1 --format="%cD" $c
    $env:GIT_COMMITTER_DATE = $cDate
    $env:GIT_AUTHOR_DATE = $cDate
    git cherry-pick $c
    
    if ($c -eq "2c0a931") {
        git rm rewrite.ps1
        git commit --amend --no-edit
    }
}

git branch -f main HEAD
git checkout main
git branch -D temp_split

Remove-Item split.ps1 -ErrorAction SilentlyContinue
