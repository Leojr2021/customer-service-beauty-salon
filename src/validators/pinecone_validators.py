
from pydantic import BaseModel, Field, field_validator
import re
from typing import Dict, Annotated

class IndexNameStructure(BaseModel):
    index_name: Annotated[str, Field(description="Lower case name of the index you want to create")]

    @field_validator('index_name')
    @classmethod
    def check_letters_lowercase(cls, v):
        if not re.fullmatch(r"^[a-z]+$", v):
            raise ValueError('index_name must be only letters in lowercase')
        return v

class ExpectedNewData(BaseModel):
    new_info: Dict[str, str] = Field(description="Expected a pair key:value of question and answer.")

    @field_validator('new_info')
    @classmethod
    def check_lowercase(cls, v):
        if set(v.keys()) != {'question','answer'}:
            raise ValueError("The structure of the dictionary should be {'question':'...,' 'answer':'...'}")
        return v