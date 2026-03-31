import httpx
import itertools
from datetime import datetime, timezone

from helpers import conflicts, score_schedule, summarize_schedule, to_minutes


def register_tools(mcp, API_KEY, BASE_URL):

    @mcp.tool()
    async def list_subjects(query: str = None) -> list:
        """
        List all subjects offered at the University of Waterloo.
        Optionally filter by a search query (e.g. query="computer science", query="CS", query="engineering").
        Matches against subject code, name, and description (case-insensitive).
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/Subjects",
                headers={"X-API-KEY": API_KEY}
            )
            response.raise_for_status()
            subjects = response.json()
            if query is not None:
                q = query.lower()
                query_words = q.split()
                subjects = [
                    s for s in subjects
                    if s.get("code", "").lower().startswith(q)
                    or all(
                        any(word.startswith(qw) for word in s.get("name", "").lower().split())
                        for qw in query_words
                    )
                ]
            return [
                {
                    "code": s.get("code"),
                    "name": s.get("name"),
                    "description": s.get("description"),
                }
                for s in subjects
            ]

    @mcp.tool()
    async def list_courses(term_code: str, subject: str, level: str = None) -> list:
        """
        List all courses offered for a specific term and subject at UWaterloo.
        Returns catalog number, title, units, and academic level.
        term_code is the numeric term code (e.g. "1261" for Winter 2026). Use list_terms to find term codes.
        subject is the subject code (e.g. "CS", "ECE"). Use list_subjects to find subject codes.
        Optionally filter by level: "undergrad" or "grad".
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/Courses/{term_code}/{subject}",
                headers={"X-API-KEY": API_KEY}
            )
            response.raise_for_status()
            data = response.json()
            if level is not None:
                career_map = {"undergrad": "UG", "grad": "GR"}
                career = career_map.get(level.lower())
                if career:
                    data = [c for c in data if c.get("associatedAcademicCareer") == career]
            return [
                {
                    "catalog_number": c.get("catalogNumber"),
                    "title": c.get("title"),
                    "units": c.get("units"),
                    "academic_level": c.get("acadCareerCode"),
                }
                for c in data
            ]

    @mcp.tool()
    async def list_terms(year: int = None, season: str = None, is_active: bool = None) -> list:
        """
        List all terms offered at the University of Waterloo.
        Optionally filter by year (e.g. year=2026), season (e.g. season="Fall", "Winter", "Spring"),
        and/or is_active=True to get only the current term (today falls between termBeginDate and termEndDate).
        Use is_active=True to find the current term before querying current courses.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/Terms",
                headers={"X-API-KEY": API_KEY}
            )
            response.raise_for_status()
            terms = response.json()
            if year is not None:
                terms = [t for t in terms if str(year) in t.get("name", "")]
            if season is not None:
                terms = [t for t in terms if season.capitalize() in t.get("name", "")]
            if is_active is not None:
                now = datetime.now(timezone.utc)
                def term_is_active(t):
                    begin = t.get("termBeginDate")
                    end = t.get("termEndDate")
                    if not begin or not end:
                        return False
                    return datetime.fromisoformat(begin).replace(tzinfo=timezone.utc) <= now <= datetime.fromisoformat(end).replace(tzinfo=timezone.utc)
                terms = [t for t in terms if term_is_active(t) == is_active]
            return [
                {
                    "termCode": t.get("termCode"),
                    "name": t.get("name"),
                    "termBeginDate": t.get("termBeginDate"),
                    "termEndDate": t.get("termEndDate"),
                }
                for t in terms
            ]

    @mcp.tool()
    async def get_course_details(term_code: str, subject: str, catalog_number: str) -> dict:
        """
        Get detailed information about a specific course offered at the University of Waterloo.
        e.g. subject='CS', catalog_number='246', term_code='1261'
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/Courses/{term_code}/{subject}/{catalog_number}",
                headers={"X-API-KEY": API_KEY}
            )
            response.raise_for_status()
            return response.json()

    @mcp.tool()
    async def get_class_schedule(term_code: str, subject: str, catalog_number: str, component: str = None) -> dict:
        """
        Get the class schedule for a single specific course at UWaterloo.
        Use this for looking up one course at a time — for multiple courses use find_valid_schedules instead.
        Only current and recently published terms have schedule data available.
        Optionally filter by component type: 'LEC' for lectures, 'TUT' for tutorials, 'TST' for tests.
        e.g. subject='CS', catalog_number='246', term_code='1261', component='LEC'
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/ClassSchedules/{term_code}/{subject}/{catalog_number}",
                headers={"X-API-KEY": API_KEY}
            )

            if response.status_code == 404:
                return {
                    "course": f"{subject}{catalog_number}",
                    "term": term_code,
                    "available": False,
                    "message": "No class schedule found for this course in this term."
                }

            data = response.json()

            sections = []
            for item in data:
                schedule = item.get("scheduleData", [{}])[0]

                clean_section = {
                    "section": item.get("classSection"),
                    "component": item.get("courseComponent"),
                    "days": schedule.get("classMeetingDayPatternCode"),
                    "start_time": schedule.get("classMeetingStartTime"),
                    "end_time": schedule.get("classMeetingEndTime"),
                    "location": schedule.get("locationName"),
                    "instructor": item.get("instructorData"),
                    "enrollment_current": item.get("enrolledStudents"),
                    "enrollment_capacity": item.get("maxEnrollmentCapacity"),
                }

                sections.append(clean_section)

            if component:
                sections = [s for s in sections if s.get("component") == component.upper()]

            return {
                "course": f"{subject}{catalog_number}",
                "term": term_code,
                "available": True,
                "sections": sections
            }

    @mcp.tool()
    async def find_valid_schedules(term_code: str, courses: list[str]) -> dict:
        """
        USE THIS TOOL when the user wants to build a schedule with 2 or more courses.
        DO NOT use get_class_schedule for multi-course scheduling.
        Find all conflict-free schedule combinations for a list of courses at UWaterloo.
        courses should be a list of strings in the format "SUBJECT CATALOG_NUMBER"
        e.g. ["CS 246", "MATH 239", "STAT 230"]
        Returns only combinations with no time conflicts.
        """

        course_combos = []
        all_sections_by_course = {}

        async with httpx.AsyncClient() as http:
            for course in courses:
                subject, catalog_number = course.split()

                response = await http.get(
                    f"{BASE_URL}/ClassSchedules/{term_code}/{subject}/{catalog_number}",
                    headers={"X-API-KEY": API_KEY}
                )

                if response.status_code == 404:
                    return {"error": f"No schedule found for {course} in term {term_code}."}
                response.raise_for_status()

                data = response.json()

                grouped = {}
                for item in data:
                    schedule_data = item.get("scheduleData") or [{}]
                    times = [
                        (to_minutes(s.get("classMeetingStartTime")), to_minutes(s.get("classMeetingEndTime")))
                        for s in schedule_data
                    ]
                    first = schedule_data[0] if schedule_data else {}

                    parsed_section = {
                        "course": f"{subject} {catalog_number}",
                        "section": item.get("classSection"),
                        "component": item.get("courseComponent"),
                        "days": first.get("classMeetingDayPatternCode", ""),
                        "times": times
                    }

                    component = item.get("courseComponent", "UNKNOWN")
                    grouped.setdefault(component, []).append(parsed_section)

                all_sections_by_course[course] = [s for group in grouped.values() for s in group]

                for component_sections in grouped.values():
                    course_combos.append(component_sections)

        MAX_VALID_SCHEDULES = 10
        valid_schedules = []

        for combo in itertools.product(*course_combos):
            possible_schedule = list(combo)

            has_conflict = False

            for i in range(len(possible_schedule)):
                for j in range(i + 1, len(possible_schedule)):
                    if conflicts(possible_schedule[i], possible_schedule[j]):
                        has_conflict = True
                        break
                if has_conflict:
                    break

            if not has_conflict:
                score = score_schedule(possible_schedule)
                if len(valid_schedules) < MAX_VALID_SCHEDULES:
                    valid_schedules.append((score, possible_schedule))
                else:
                    worst_index = 0
                    for i in range(1, len(valid_schedules)):
                        if valid_schedules[i][0] > valid_schedules[worst_index][0]:
                            worst_index = i
                    if score < valid_schedules[worst_index][0]:
                        valid_schedules[worst_index] = (score, possible_schedule)

        result = {
            "term": term_code,
            "courses": courses,
            "valid_schedules": [summarize_schedule(s[1]) for s in valid_schedules]
        }

        if not valid_schedules:
            all_sections = {}
            for course, sections in all_sections_by_course.items():
                all_sections[course] = [
                    {
                        "section": s["section"],
                        "component": s["component"],
                        "days": s["days"],
                        "times": s["times"]
                    }
                    for s in sections
                ]
            result["all_sections"] = all_sections

        return result


