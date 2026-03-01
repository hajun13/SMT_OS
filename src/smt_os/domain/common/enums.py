from __future__ import annotations

from enum import Enum


class EventTemplate(str, Enum):
    DAY_EVENT = "day_event"
    CAMP = "camp"


class RegistrationKind(str, Enum):
    INDIVIDUAL = "individual"
    GROUP = "group"


class CheckinType(str, Enum):
    ENTRY = "entry"
    MEAL = "meal"
    ACTIVITY = "activity"
    SESSION = "session"


class RoleType(str, Enum):
    ORG_ADMIN = "org_admin"
    EVENT_ADMIN = "event_admin"
    STAFF = "staff"
    LEADER = "leader"
    PARTICIPANT = "participant"


class FieldType(str, Enum):
    TEXT = "text"
    TEXTAREA = "textarea"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    CHECKBOX = "checkbox"
    DATE = "date"
    PHONE = "phone"


class SurveyQuestionType(str, Enum):
    RATING = "rating"
    TEXT = "text"
    SINGLE_CHOICE = "single_choice"
