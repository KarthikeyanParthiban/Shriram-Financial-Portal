import os
import shutil

dst = "d:\\Projects\\Github\\SAMC Micro digest"

to_delete = [
    "Project_Market_Digest_Complete_Documentation.docx",
    "Project_Market_Digest_Complete_Documentation.md",
    "Project_Architecture.md",
    "StonkzzReport-30Sep.pdf",
    "generate_podcast.py",
    "extract_ref_pdf_text.py",
    "list_teams.py",
    "post_to_teams.py",
    "render_pdf_pages.py",
    "render_ref_pdf.py",
    "send_one_time_yogeshwaran.py",
    "run_daily.ps1",
    "schedule_task.ps1",
    "market_digest/templates/report.html.j2"
]

print("Starting cleanup in SAMC Micro digest...")
for file in to_delete:
    path = os.path.join(dst, file.replace("/", "\\"))
    if os.path.exists(path):
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
                print(f"  Deleted directory: {file}")
            else:
                os.remove(path)
                print(f"  Deleted file: {file}")
        except Exception as e:
            print(f"  Error deleting {file}: {e}")
    else:
        print(f"  File not found (already clean): {file}")

print("Cleanup completed.")
