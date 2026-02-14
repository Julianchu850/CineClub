import tmdbsimple as tmdb
import os
from dotenv import load_dotenv

load_dotenv()

tmdb.API_KEY = os.getenv("TMDB_API_KEY")

TMDB_LANGUAGE = os.getenv("TMDB_LANGUAGE", "es-MX")  
TMDB_REGION = os.getenv("TMDB_REGION", "MX") 


def search_movie(query: str):
    search = tmdb.Search()
    search.movie(query=query, language=TMDB_LANGUAGE, region=TMDB_REGION)
    return search.results


def get_movie_details(tmdb_id: int):
    movie = tmdb.Movies(tmdb_id)

    # Request Spanish (LatAm) + credits in the same response
    details = movie.info(
        language=TMDB_LANGUAGE,
        append_to_response="credits"
    )

    # Optional fallback: if Spanish overview/tagline missing, fill from EN
    if not details.get("overview") or not details.get("tagline"):
        en = movie.info(language="en-US", append_to_response="credits")
        details["overview"] = details.get("overview") or en.get("overview")
        details["tagline"] = details.get("tagline") or en.get("tagline")

    return details


def get_person_imdb_id(person_id: int):
    person = tmdb.People(person_id)
    external = person.external_ids()
    return external.get("imdb_id")


def get_person_imdb_url(person_id: int):
    imdb_id = get_person_imdb_id(person_id)
    if imdb_id:
        return f"https://www.imdb.com/name/{imdb_id}/"
    return None