from enum import Enum


class CustomEnum(Enum):
    @classmethod
    def values(cls):
        return [cls.__dict__.get('_member_map_')[k].value for k in cls.__dict__.get('_member_map_')]

    @classmethod
    def keys(cls):
        return [k for k in cls.__dict__.get('_member_map_')]

    @classmethod
    def valueof(cls, key):
        data = cls.__dict__.get('_member_map_')[key]
        if not data:
            return None
        return data.value

    @classmethod
    def get(cls, key):
        data = cls.__dict__.get('_member_map_')[key]
        if not data:
            return None
        return data
