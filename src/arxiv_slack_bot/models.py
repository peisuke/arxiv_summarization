from pydantic import BaseModel


class Result(BaseModel):
    overview: str
    problem: str
    contribution: str
    conclusion: str