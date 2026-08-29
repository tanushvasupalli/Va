# Setup GitHub Connection for Wednesday Voice Agent
# This script configures Git user settings, creates the initial commit, and hooks up the remote repository.

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "       GitHub Setup for Wednesday AI Agent       " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Check Git configuration
$gitName = git config --global user.name
$gitEmail = git config --global user.email

if (-not $gitName) {
    Write-Host "`n[!] Git User Name is not configured globally." -ForegroundColor Yellow
    $newName = Read-Host "Enter your Git/GitHub name (e.g. John Doe)"
    if ($newName) {
        git config --global user.name "$newName"
        Write-Host "Saved global user.name as: $newName" -ForegroundColor Green
    }
} else {
    Write-Host "Git Name: $gitName" -ForegroundColor Green
}

if (-not $gitEmail) {
    Write-Host "`n[!] Git User Email is not configured globally." -ForegroundColor Yellow
    $newEmail = Read-Host "Enter your Git/GitHub email (e.g. john@example.com)"
    if ($newEmail) {
        git config --global user.email "$newEmail"
        Write-Host "Saved global user.email as: $newEmail" -ForegroundColor Green
    }
} else {
    Write-Host "Git Email: $gitEmail" -ForegroundColor Green
}

# 2. Stage files
Write-Host "`nStaging all project files..." -ForegroundColor Gray
git add .

# 3. Create initial commit
$status = git status --porcelain
if ($status) {
    Write-Host "Creating initial commit..." -ForegroundColor Gray
    git commit -m "Initial commit: Wednesday Personal AI Voice Agent"
    Write-Host "Created initial commit successfully!" -ForegroundColor Green
} else {
    Write-Host "No changes to commit or commit already exists." -ForegroundColor Gray
}

# 4. Set branch name to main
git branch -M main

# 5. Connect to GitHub Remote
$currentRemote = git remote get-url origin 2>$null
if ($currentRemote) {
    Write-Host "`n[i] Already connected to remote: $currentRemote" -ForegroundColor Cyan
    $changeRemote = Read-Host "Do you want to change this remote? (y/N)"
    if ($changeRemote -eq "y" -or $changeRemote -eq "Y") {
        git remote remove origin
        $currentRemote = $null
    }
}

if (-not $currentRemote) {
    Write-Host "`n[Instructions]" -ForegroundColor Yellow
    Write-Host "1. Open https://github.com and log in."
    Write-Host "2. Create a new repository (name it 'Wednesday' or whatever you like)."
    Write-Host "3. Leave it empty (do NOT add README, .gitignore, or license)."
    Write-Host "4. Copy the repository URL (should look like https://github.com/username/repo.git).`n"
    
    $repoUrl = Read-Host "Enter your GitHub repository URL"
    if ($repoUrl) {
        git remote add origin $repoUrl.Trim()
        Write-Host "Linked local repository to: $repoUrl" -ForegroundColor Green
    } else {
        Write-Host "No URL entered. Skipping remote link. You can add it later using:" -ForegroundColor Yellow
        Write-Host "git remote add origin <your-repo-url>" -ForegroundColor Yellow
    }
}

# 6. Push to GitHub
$currentRemote = git remote get-url origin 2>$null
if ($currentRemote) {
    Write-Host "`nReady to push code to GitHub!" -ForegroundColor Cyan
    $pushNow = Read-Host "Do you want to push to main branch now? (y/N)"
    if ($pushNow -eq "y" -or $pushNow -eq "Y") {
        Write-Host "Pushing to GitHub..." -ForegroundColor Gray
        git push -u origin main
    } else {
        Write-Host "`nYou can push manually later by running:" -ForegroundColor Yellow
        Write-Host "git push -u origin main" -ForegroundColor Yellow
    }
}

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "Setup script finished!" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
