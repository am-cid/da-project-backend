from enum import StrEnum


class PageChartType(StrEnum):
    BAR_CHART = "BAR_CHART"
    PIE_CHART = "PIE_CHART"
    TREND_CHART = "TREND_CHART"
    SCATTER_PLOT = "SCATTER_PLOT"


class ColumnDataType(StrEnum):
    BOOLEAN = "BOOLEAN"
    NUMBER = "NUMBER"
    STRING = "STRING"
