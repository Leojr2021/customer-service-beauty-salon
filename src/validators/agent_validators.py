from pydantic import BaseModel, Field, field_validator
import re
from typing import Annotated


class DateTimeModel(BaseModel):
    """
    The way the date should be structured and formatted
    """
    date: Annotated[str, Field(pattern=r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$')]

    @field_validator("date")
    @classmethod
    def check_format_date(cls, v):
        if not re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$', v):
            raise ValueError("The date should be in format 'YYYY-MM-DD HH:MM'")
        return v

class DateModel(BaseModel):
    """
    The way the date should be structured and formatted
    """
    date: Annotated[str, Field(pattern=r'^\d{4}-\d{2}-\d{2}$')]

    @field_validator("date")
    @classmethod
    def check_format_date(cls, v):
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError("The date must be in the format 'YYYY-MM-DD'")
        return v

    
class IdentificationNumberModel(BaseModel):
    """
    The way the ID should be structured and formatted
    """
    id: str

    @field_validator("id")
    @classmethod
    def check_format_id(cls, v):
        try:
            id_int = int(v)
            if not 1000000 <= id_int <= 99999999:
                raise ValueError("The ID number should be a number between 1000000 and 99999999")
        except ValueError:
            raise ValueError("The ID number should be a valid integer")
        return str(id_int)  # Return as string to maintain consistency
