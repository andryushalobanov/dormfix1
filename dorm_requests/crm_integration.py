import json
import logging
from dataclasses import dataclass
from typing import Optional, Any

import requests as http_requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class CRMResult:
    success: bool
    crm_id: Optional[str] = None
    error: Optional[str] = None
    response: Optional[dict] = None


def _load_json_setting(setting_name: str) -> dict:
    """
    Читает JSON-словарь из settings.

    Используется для:
    - BITRIX24_CATEGORY_ENUM_MAP
    - BITRIX24_STATUS_ENUM_MAP
    - BITRIX24_MASTER_USER_MAP
    """
    raw_value = getattr(settings, setting_name, '{}') or '{}'

    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        logger.exception("Invalid JSON in setting %s", setting_name)
        return {}


def _call_bitrix24_method(method: str, payload: dict) -> CRMResult:
    """
    Выполняет POST-запрос в Bitrix24 через входящий webhook.

    Пример method:
    - crm.lead.add
    """

    webhook_base_url = settings.BITRIX24_WEBHOOK_BASE_URL.strip()

    if not webhook_base_url:
        return CRMResult(
            success=False,
            error="BITRIX24_WEBHOOK_BASE_URL is not configured"
        )

    url = f"{webhook_base_url.rstrip('/')}/{method}.json"

    try:
        response = http_requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()

        if 'error' in data:
            return CRMResult(
                success=False,
                error=f"{data.get('error')}: {data.get('error_description')}",
                response=data
            )

        return CRMResult(
            success=True,
            crm_id=str(data.get('result')) if data.get('result') is not None else None,
            response=data
        )

    except http_requests.RequestException as exc:
        logger.exception("Bitrix24 request failed")
        return CRMResult(success=False, error=str(exc))

    except ValueError as exc:
        logger.exception("Bitrix24 returned invalid JSON")
        return CRMResult(success=False, error=f"Invalid JSON response: {exc}")


def _get_profile(application):
    return getattr(application.user, 'profile', None)


def _get_student_full_name(application) -> str:
    profile = _get_profile(application)

    if profile and profile.full_name:
        return profile.full_name

    user_full_name = application.user.get_full_name()
    if user_full_name:
        return user_full_name

    return application.user.username


def _get_student_phone(application) -> str:
    profile = _get_profile(application)
    return profile.phone if profile and profile.phone else ''


def _get_room_number(application) -> str:
    profile = _get_profile(application)
    return profile.room_number if profile and profile.room_number else ''


def _get_category_name(application) -> str:
    return application.category.name if application.category else 'Без категории'


def _get_category_value_for_bitrix(application) -> Any:
    """
    У тебя Problem Category в Bitrix24 — поле типа Список.

    Поэтому Bitrix24 ждёт ID значения:
    - Сантехника -> 44
    - Электрика -> 46
    - Интернет -> 48
    - Мебель -> 50
    - Бытовая техника -> 52
    """
    category_name = _get_category_name(application)
    enum_map = _load_json_setting('BITRIX24_CATEGORY_ENUM_MAP')
    return enum_map.get(category_name, category_name)


def _get_status_value_for_bitrix(application) -> Any:
    """
    У тебя Application Status в Bitrix24 — поле типа Список.

    В Django статус хранится так:
    - new
    - in_progress
    - completed
    - cancelled

    В Bitrix24 нужно передавать ID:
    - new -> 54
    - in_progress -> 56
    - completed -> 58
    - cancelled -> 60
    """
    enum_map = _load_json_setting('BITRIX24_STATUS_ENUM_MAP')
    return enum_map.get(application.status, application.get_status_display())


def _get_master_bitrix_user_id(application) -> Optional[str]:
    """
    Assigned Master в Bitrix24 имеет тип employee.

    Значит Bitrix24 ждёт ID сотрудника Bitrix24, а не текстовое имя.

    Сейчас при создании заявки мастер обычно ещё не назначен,
    поэтому это поле можно не передавать.
    """
    if not application.assigned_to:
        return None

    user_map = _load_json_setting('BITRIX24_MASTER_USER_MAP')

    username = application.assigned_to.username
    email = application.assigned_to.email

    return user_map.get(username) or user_map.get(email)


def _format_datetime_for_bitrix(dt) -> str:
    """
    У тебя поле DormFix Created At в Bitrix24 имеет тип datetime.

    Отправляем дату в понятном формате без микросекунд.
    """
    local_dt = timezone.localtime(dt)
    return local_dt.strftime('%Y-%m-%dT%H:%M:%S')


def _add_custom_field(fields: dict, field_code: str, value: Any) -> None:
    """
    Добавляет пользовательское поле Bitrix24 в payload.

    Пустые коды не добавляет.
    None не добавляет.
    """
    if not field_code:
        return

    if value is None:
        return

    fields[field_code] = value


def build_lead_fields_from_application(application) -> dict:
    """
    Собирает поля лида Bitrix24 из заявки DormFix.

    Источники данных в твоём проекте:
    - Application.id
    - Application.category.name
    - Application.description
    - Application.status
    - Application.created_at
    - Application.assigned_to
    - UserProfile.full_name
    - UserProfile.room_number
    - UserProfile.phone
    """

    category_name = _get_category_name(application)
    student_full_name = _get_student_full_name(application)
    student_phone = _get_student_phone(application)
    room_number = _get_room_number(application)

    fields = {
        'TITLE': f'Заявка DormFix #{application.id}: {category_name}',
        'NAME': student_full_name,
        'COMMENTS': application.description,
        'SOURCE_DESCRIPTION': 'DormFix web application',
    }

    if student_phone:
        fields['PHONE'] = [
            {
                'VALUE': student_phone,
                'VALUE_TYPE': 'WORK'
            }
        ]

    if application.user.email:
        fields['EMAIL'] = [
            {
                'VALUE': application.user.email,
                'VALUE_TYPE': 'WORK'
            }
        ]

    # DormFix Application ID
    # В Bitrix24 это поле типа double, поэтому передаём число.
    _add_custom_field(
        fields,
        settings.BITRIX24_FIELD_APPLICATION_ID,
        float(application.id)
    )

    # Room Number
    _add_custom_field(
        fields,
        settings.BITRIX24_FIELD_ROOM_NUMBER,
        room_number
    )

    # Problem Category
    _add_custom_field(
        fields,
        settings.BITRIX24_FIELD_CATEGORY,
        _get_category_value_for_bitrix(application)
    )

    # Application Status
    _add_custom_field(
        fields,
        settings.BITRIX24_FIELD_STATUS,
        _get_status_value_for_bitrix(application)
    )

    # Assigned Master
    # Это поле необязательное. Если мастер не назначен — не отправляем.
    master_bitrix_user_id = _get_master_bitrix_user_id(application)
    if master_bitrix_user_id:
        _add_custom_field(
            fields,
            settings.BITRIX24_FIELD_ASSIGNED_MASTER,
            master_bitrix_user_id
        )

    # DormFix Created At
    _add_custom_field(
        fields,
        settings.BITRIX24_FIELD_CREATED_AT,
        _format_datetime_for_bitrix(application.created_at)
    )

    # Source System
    _add_custom_field(
        fields,
        settings.BITRIX24_FIELD_SOURCE_SYSTEM,
        'DormFix'
    )

    return fields


def create_crm_lead_for_application(application) -> CRMResult:
    """
    Создаёт лид в Bitrix24 на основе заявки DormFix.

    Вызывается сразу после создания Application.
    """

    fields = build_lead_fields_from_application(application)

    payload = {
        'fields': fields,
        'params': {
            'REGISTER_SONET_EVENT': 'Y'
        }
    }

    return _call_bitrix24_method('crm.lead.add', payload)