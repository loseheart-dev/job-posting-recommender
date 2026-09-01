from src.config import CLEANED_DATA_PATH
from src.data.loader import load_jobs
from src.ui.pages import render_home


def main() -> None:
    jobs = load_jobs(CLEANED_DATA_PATH)
    render_home(jobs)


if __name__ == "__main__":
    main()
