REPO_NAME="test_repo"
poetry run adev repo $REPO_NAME -t autonomy
cd $REPO_NAME
cp poetry.lock ../auto_dev/data/repo/templates/autonomy/