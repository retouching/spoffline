import os
from uuid import UUID

project_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../')


def is_valid_uuid(raw_uuid, version=4):
    if type(raw_uuid) != UUID:
        try:
            UUID(raw_uuid, version=version)
        except ValueError:
            return False
    return True
