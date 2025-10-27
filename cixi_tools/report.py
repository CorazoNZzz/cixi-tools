"""Core parsing and formatting logic for the simplified source tracing report."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Iterable, List, Optional


@dataclass
class ReportData:
    """Structured information extracted from the raw incident description."""

    alarm_time: datetime
    travel_time: Optional[datetime]
    station_name: str
    station_code: Optional[str]
    high_value_location: str
    anomaly_location: str
    wind_direction: str
    scene_descriptions: List[str]
    peak_value_ug_m3: Optional[float]
    gcms_factors: List[str]
    suspected_enterprise: Optional[str]


_TIME_PATTERN = re.compile(
    r"(?P<year>\d{4})年(?P<month>\d{1,2})月(?P<day>\d{1,2})日(?P<hour>\d{1,2})时"
)
_TRAVEL_TIME_PATTERN = re.compile(
    r"(?:(?P<month>\d{1,2})月(?P<day>\d{1,2})日)?(?P<hour>\d{1,2})[:：](?P<minute>\d{1,2})"
)
_PEAK_PATTERN = re.compile(
    r"峰值[^\d]*(?P<value>\d+(?:\.\d+)?)\s*(?:ug/m3|µg/m³|μg/m³)",
    re.IGNORECASE,
)


def _extract_station(raw: str) -> tuple[str, Optional[str]]:
    match = re.search(r"([\w\u4e00-\u9fff]+)(?:（(?P<code>[^）]+)）)?TVOC站", raw)
    if not match:
        cleaned = raw.replace("报警", "").strip("，。 ")
        return cleaned, None

    name = match.group(1)
    code = match.group("code")
    station = f"{name}TVOC站"
    return station, code


def _normalise_location(text: str) -> str:
    cleaned = text.strip("。：； ")
    return cleaned.replace("镇镇", "镇")


def _split_scene_descriptions(text: str) -> List[str]:
    fragments = re.split(r"[，、]", text)
    return [frag.strip() for frag in fragments if frag.strip()]


def parse_report_text(text: str) -> ReportData:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("No content provided for report parsing.")

    first_line = lines[0]
    time_match = _TIME_PATTERN.search(first_line)
    if not time_match:
        raise ValueError("Unable to locate the alarm time in the input text.")
    alarm_time = datetime(
        year=int(time_match.group("year")),
        month=int(time_match.group("month")),
        day=int(time_match.group("day")),
        hour=int(time_match.group("hour")),
        minute=0,
    )

    station_name, station_code = _extract_station(first_line)

    travel_time: Optional[datetime] = None
    high_value_location = ""
    anomaly_location = ""
    wind_direction = ""
    scene_text = ""
    peak_value: Optional[float] = None
    gcms_factors: List[str] = []
    suspected_enterprise: Optional[str] = None

    for line in lines[1:]:
        if "高值点位" in line:
            high_value_location = _normalise_location(line.split("：", 1)[-1])
        elif line.startswith("时间"):
            travel_time_match = _TRAVEL_TIME_PATTERN.search(line)
            if travel_time_match:
                month = travel_time_match.group("month")
                day = travel_time_match.group("day")
                hour = int(travel_time_match.group("hour"))
                minute = int(travel_time_match.group("minute"))
                if month and day:
                    travel_time = datetime(
                        year=alarm_time.year,
                        month=int(month),
                        day=int(day),
                        hour=hour,
                        minute=minute,
                    )
                else:
                    travel_time = alarm_time.replace(hour=hour, minute=minute)
        elif line.startswith("异常点位位置"):
            anomaly_location = _normalise_location(line.split("：", 1)[-1])
        elif line.startswith("现场风向"):
            parts = re.split(r"现场情况[:：]", line)
            wind_direction = (
                parts[0].split("：", 1)[-1].strip("，。 ")
                if parts
                else ""
            )
            if len(parts) > 1:
                scene_text = parts[1].strip()
        elif line.lower().startswith("gcms") or "gcms" in line.lower():
            payload = line.split("：", 1)[-1]
            gcms_factors = [
                factor.strip()
                for factor in re.split(r"[，,]", payload)
                if factor.strip()
            ]
        elif line.startswith("疑似企业"):
            suspected_enterprise = line.split("：", 1)[-1].strip()

    if not high_value_location:
        raise ValueError("Missing high value location information.")
    if not anomaly_location:
        raise ValueError("Missing anomaly location information.")
    if not wind_direction:
        raise ValueError("Missing wind direction information.")
    if not gcms_factors:
        raise ValueError("No GC-MS factors could be identified.")

    peak_match = _PEAK_PATTERN.search(scene_text)
    if peak_match:
        peak_value = float(peak_match.group("value"))
        scene_text = scene_text.replace(peak_match.group(0), "")

    scene_descriptions = _split_scene_descriptions(scene_text)

    return ReportData(
        alarm_time=alarm_time,
        travel_time=travel_time,
        station_name=station_name,
        station_code=station_code,
        high_value_location=high_value_location,
        anomaly_location=anomaly_location,
        wind_direction=wind_direction,
        scene_descriptions=scene_descriptions,
        peak_value_ug_m3=peak_value,
        gcms_factors=gcms_factors,
        suspected_enterprise=suspected_enterprise,
    )


def _format_station(data: ReportData) -> str:
    if data.station_code:
        return f"{data.station_name}（{data.station_code}）"
    return data.station_name


def _format_time_span(alarm_time: datetime, travel_time: Optional[datetime]) -> str:
    base = alarm_time.strftime("%Y-%m-%d %H:%M 报警")
    if not travel_time:
        return base
    suffix = travel_time.strftime("%H:%M 走航")
    if travel_time.date() != alarm_time.date():
        suffix = travel_time.strftime("%Y-%m-%d %H:%M 走航")
    return f"{base}；{suffix}"


def _is_location_fragment(fragment: str, data: ReportData) -> bool:
    if fragment.endswith("附近") or "交叉口" in fragment:
        return True

    for location in (data.high_value_location, data.anomaly_location):
        if not location:
            continue
        if fragment in location or location in fragment:
            return True
    return False


def _format_scene(data: ReportData) -> str:
    fragments: List[str] = [data.wind_direction]
    fragments.extend(
        frag
        for frag in data.scene_descriptions
        if not _is_location_fragment(frag, data)
    )
    fragments = [frag for frag in fragments if frag]
    body = "、".join(fragments)

    if data.peak_value_ug_m3 is not None:
        return f"{body}；峰值≈{data.peak_value_ug_m3:g} μg/m³"
    return body


def _format_gcms(factors: Iterable[str]) -> str:
    return "、".join(factors)


def _format_judgement(data: ReportData) -> str:
    suspected = data.suspected_enterprise or "待确认企业"
    return (
        f"在{data.wind_direction}条件下，高值区位于上述路段，"
        f"呈溶剂型复合特征；疑似来源为：{suspected}"
    )


DEFAULT_ACTIONS = (
    "面域排查：对应风向上游的涉溶剂企业群开展简要巡查（看工况、治理设施是否运行；只做点检）。",
    "数据核对：对齐站点分钟值+风向与走航记录，确认指向一致性。",
    "加密复测：在香山路—波涛路轴线于当晚/次日早高峰各复测一次；如仍偏高，再组织针对性执法。",
)


def generate_report(text: str, actions: Iterable[str] = DEFAULT_ACTIONS) -> str:
    """Generate a simplified source tracing report from raw text."""

    data = parse_report_text(text)

    lines = [
        f"时间：{_format_time_span(data.alarm_time, data.travel_time)}",
        f"站点：{_format_station(data)}",
        (
            "位置："
            f"{data.high_value_location}；{data.anomaly_location}"
        ),
        f"现场：{_format_scene(data)}",
        f"GC-MS：{_format_gcms(data.gcms_factors)}",
        f"研判：{_format_judgement(data)}",
        "处置建议：",
    ]

    for action in actions:
        lines.append(action)

    return "\n".join(lines)
