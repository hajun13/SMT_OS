from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from smt_os.application.ports.repositories import EventRepository, RegistrationFormRepository
from smt_os.domain.common.enums import FieldType
from smt_os.domain.forms.entities import FormField, RegistrationForm


class RegistrationFormEventNotFoundError(ValueError):
    pass


@dataclass(slots=True)
class FieldInput:
    key: str
    label: str
    type: FieldType
    required: bool = False
    options: list[str] = field(default_factory=list)
    sort_order: int = 0


@dataclass(slots=True)
class UpsertRegistrationFormCommand:
    event_id: str
    fields: list[FieldInput]


class UpsertRegistrationFormUseCase:
    def __init__(self, events: EventRepository, forms: RegistrationFormRepository) -> None:
        self._events = events
        self._forms = forms

    def execute(self, command: UpsertRegistrationFormCommand) -> RegistrationForm:
        event = self._events.get(command.event_id)
        if event is None:
            raise RegistrationFormEventNotFoundError("event not found")

        active_form = self._forms.get_active(command.event_id)
        if active_form is None:
            active_form = RegistrationForm(
                id=str(uuid4()),
                event_id=command.event_id,
                version=1,
                is_active=True,
            )
            self._forms.save(active_form)

        fields = [
            FormField(
                id=str(uuid4()),
                form_id=active_form.id,
                key=item.key,
                label=item.label,
                type=item.type,
                required=item.required,
                options=item.options,
                sort_order=item.sort_order,
            )
            for item in command.fields
        ]
        self._forms.replace_fields(active_form.id, fields)
        return active_form
