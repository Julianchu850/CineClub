from sqlalchemy import Column, Integer, String, Float, Date
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
status = Column(String)  

class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, index=True)

    tmdb_id = Column(Integer, unique=True, index=True, nullable=False)
    title = Column(String)
    date_watched = Column(String)

    status = Column(String)  

class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, index=True)
    movie_id = Column(Integer)
    member_name = Column(String)
    score = Column(Float)

class FamilyMember(Base):
    __tablename__ = "family_members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
