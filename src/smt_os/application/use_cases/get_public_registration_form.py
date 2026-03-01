from __future__ import annotations

from dataclasses import dataclass

from smt_os.application.ports.repositories import RegistrationFormRepository


@dataclass(slots=True)
class PublicFieldView:
    key: str
    label: str
    type: str
    required: bool
    options: list[str]
    sort_order: int


class GetPublicRegistrationFormUseCase:
    def __init__(self, forms: RegistrationFormRepository) -> None:
        self._forms = forms

    def execute(self, event_id: str) -> list[PublicFieldView]:
        active_form = self._forms.get_active(event_id)
        if active_form is None:
            return []
        fields = self._forms.list_fields(active_form.id)
        return [
            PublicFieldView(
                key=item.key,
                label=item.label,
                type=item.type.value,
                required=item.required,
                options=item.options,
                sort_order=item.sort_order,
            )
            for item in fields
        ]
