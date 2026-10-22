"""Upload an explicitly selected local folder to a Hugging Face model repository."""
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True, help="Local model/artifact folder")
    parser.add_argument("--repo-id", required=True, help="YOUR_USERNAME/repository-name")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        raise SystemExit(f"Folder does not exist: {folder}")
    print(f"About to upload '{folder}' to public/private repo '{args.repo_id}'.")
    print("Verify the folder contains no secrets, personal data, or unlicensed files.")
    if input("Type UPLOAD to continue: ").strip() != "UPLOAD":
        print("Cancelled.")
        return

    from huggingface_hub import HfApi
    api = HfApi()
    api.create_repo(repo_id=args.repo_id, repo_type="model", exist_ok=True)
    result = api.upload_folder(folder_path=str(folder), repo_id=args.repo_id, repo_type="model")
    print(f"Upload finished: {result}")

if __name__ == "__main__":
    main()
