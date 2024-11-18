from enum import StrEnum


## MODEL TYPES
class PageChartType(StrEnum):
    BAR_CHART = "BAR_CHART"
    PIE_CHART = "PIE_CHART"
    TREND_CHART = "TREND_CHART"
    SCATTER_PLOT = "SCATTER_PLOT"


class ColumnDataType(StrEnum):
    BOOLEAN = "BOOLEAN"
    NUMBER = "NUMBER"
    STRING = "STRING"


## API TYPES
class ColumnOperation(StrEnum):
    FIRST = "first"
    LAST = "last"
    MAX = "max"
    MEAN = "mean"
    MEDIAN = "median"
    MIN = "min"
    MODE = "mode"
    SUM = "sum"
