from __future__ import annotations

import textwrap

from cixi_tools import generate_report, parse_report_text


RAW_TEXT = textwrap.dedent(
    """
    2025年10月28日08时，慈东工业区（119）TVOC站报警。
    高值点位：龙山镇镇滨海工业园（VOCs走航）
    时间：10月28日10：15
    异常点位位置：香山路与波涛路交叉口附近，瑞鑫光学薄膜有限公司北侧
    现场风向：东北风 现场情况:香山路与波涛路附近峰值浓度300ug/m3，现场实时风速较高扩散且范围较大
    gcms因子：甲苯，苯，二氯甲烷，丁烷，六氟丙酮，乙基苯
    疑似企业：浙江新韩剑高分子科技有限公司
    """
).strip()


EXPECTED_REPORT = textwrap.dedent(
    """
    时间：2025-10-28 08:00 报警；10:15 走航
    站点：慈东工业区TVOC站（119）
    位置：龙山镇滨海工业园（VOCs走航）；香山路与波涛路交叉口附近，瑞鑫光学薄膜有限公司北侧
    现场：东北风、现场实时风速较高扩散且范围较大；峰值≈300 μg/m³
    GC-MS：甲苯、苯、二氯甲烷、丁烷、六氟丙酮、乙基苯
    研判：在东北风条件下，高值区位于上述路段，呈溶剂型复合特征；疑似来源为：浙江新韩剑高分子科技有限公司
    处置建议：
    面域排查：对应风向上游的涉溶剂企业群开展简要巡查（看工况、治理设施是否运行；只做点检）。
    数据核对：对齐站点分钟值+风向与走航记录，确认指向一致性。
    加密复测：在香山路—波涛路轴线于当晚/次日早高峰各复测一次；如仍偏高，再组织针对性执法。
    """
).strip()


def test_parse_report_text_extracts_core_fields():
    data = parse_report_text(RAW_TEXT)
    assert data.alarm_time.strftime("%Y-%m-%d %H:%M") == "2025-10-28 08:00"
    assert data.travel_time.strftime("%H:%M") == "10:15"
    assert data.station_name == "慈东工业区TVOC站"
    assert data.station_code == "119"
    assert data.high_value_location.startswith("龙山镇")
    assert data.anomaly_location.startswith("香山路")
    assert data.wind_direction == "东北风"
    assert "现场实时风速较高扩散且范围较大" in data.scene_descriptions
    assert data.peak_value_ug_m3 == 300
    assert "甲苯" in data.gcms_factors
    assert data.suspected_enterprise == "浙江新韩剑高分子科技有限公司"


def test_generate_report_matches_expected_output():
    report = generate_report(RAW_TEXT)
    assert report == EXPECTED_REPORT
