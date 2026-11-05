"""Shared academic-year helpers.  Save as  apps/academic_year.py
(next to dbconnect.py).  Used by Class Profiles, Student Details and
the School Health Records pages.
"""
from apps import dbconnect as db

QUARTERS = ["1st Quarter", "2nd Quarter", "3rd Quarter", "4th Quarter"]
FIRST_SCHOOL_YEAR = "2026-2027"

# SQL expressions that DERIVE age from the stored birthdate (age is not stored).
# Use with a student alias of `s`, or pass the column name you need.
def age_years_sql(col="s.student_birthdate"):
    return f"EXTRACT(YEAR FROM AGE(CURRENT_DATE, {col}))::int"


def age_months_sql(col="s.student_birthdate"):
    return (
        f"(EXTRACT(YEAR FROM AGE(CURRENT_DATE, {col})) * 12 "
        f"+ EXTRACT(MONTH FROM AGE(CURRENT_DATE, {col})))::int"
    )


def cycle_label(school_year, quarter):
    return f"{school_year} - {quarter}"


def school_year_from_semester(semester):
    """'2026-2027 - 1st Quarter' -> '2026-2027'."""
    text = (semester or "").strip()
    return text.rsplit(" - ", 1)[0].strip() if " - " in text else None


def quarter_from_semester(semester):
    text = (semester or "").strip()
    return text.rsplit(" - ", 1)[1].strip() if " - " in text else None


def next_school_year(school_year):
    start, end = (int(part) for part in school_year.split("-"))
    return f"{start + 1}-{end + 1}"


def ensure_quarter_cycles(school_year):
    """Create any missing quarter rows in program_cycle for the school year."""
    for quarter in QUARTERS:
        label = cycle_label(school_year, quarter)
        existing = db.getDataFromDB(
            """SELECT cycle_id FROM program_cycle
               WHERE LOWER(BTRIM(semester)) = LOWER(BTRIM(%s)) LIMIT 1""",
            [label], ["cycle_id"],
        )
        if existing is None or existing.empty:
            db.modifyDB("INSERT INTO program_cycle (semester) VALUES (%s)", [label])


def get_current_school_year():
    """The one open (not ended) academic year; created if none exists yet."""
    df = db.getDataFromDB(
        """SELECT school_year FROM academic_year
           WHERE NOT acad_year_ended_ind
           ORDER BY school_year DESC LIMIT 1""",
        [], ["school_year"],
    )
    if df is not None and not df.empty:
        year = str(df.iloc[0]["school_year"])
    else:
        latest = db.getDataFromDB(
            "SELECT school_year FROM academic_year ORDER BY school_year DESC LIMIT 1",
            [], ["school_year"],
        )
        year = (
            FIRST_SCHOOL_YEAR if latest is None or latest.empty
            else next_school_year(str(latest.iloc[0]["school_year"]))
        )
        db.modifyDB(
            "INSERT INTO academic_year (school_year) VALUES (%s) "
            "ON CONFLICT (school_year) DO NOTHING",
            [year],
        )
    ensure_quarter_cycles(year)
    return year


def is_year_ended(school_year):
    if not school_year:
        return False
    df = db.getDataFromDB(
        "SELECT acad_year_ended_ind FROM academic_year WHERE school_year = %s",
        [school_year], ["ended"],
    )
    return bool(df is not None and not df.empty and df.iloc[0]["ended"])


def get_school_year_options():
    """Dropdown options, newest first. Ended years are labelled."""
    get_current_school_year()  # makes sure at least one year exists
    df = db.getDataFromDB(
        """SELECT school_year, acad_year_ended_ind
           FROM academic_year ORDER BY school_year DESC""",
        [], ["school_year", "ended"],
    )
    options = []
    for _, row in df.iterrows():
        year = str(row["school_year"])
        label = f"{year} (ended)" if bool(row["ended"]) else f"{year} (current)"
        options.append({"label": label, "value": year})
    return options


def end_current_school_year():
    """Close the open year and open the next one. Returns (ended, new)."""
    ended = get_current_school_year()
    new_year = next_school_year(ended)
    # End first: the unique index allows only one open year at a time.
    db.modifyDB(
        """UPDATE academic_year
           SET acad_year_ended_ind = TRUE, acad_year_end_date = CURRENT_DATE
           WHERE school_year = %s""",
        [ended],
    )
    db.modifyDB(
        "INSERT INTO academic_year (school_year) VALUES (%s) "
        "ON CONFLICT (school_year) DO NOTHING",
        [new_year],
    )
    ensure_quarter_cycles(new_year)
    return ended, new_year