from enum import StrEnum


## MODEL TYPES
class PageChartType(StrEnum):
    SCATTER_PLOT = "SCATTER_PLOT"
    PIE_CHART = "PIE_CHART"
    BUBBLE_CHART = "BUBBLE_CHART"
    FUNNEL_CHART = "FUNNEL_CHART"
    GEOCHART = "GEOCHART"


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


class FillNullStrategy(StrEnum):
    FORWARD = "forward"
    BACKWARD = "backward"
    MIN = "min"
    MAX = "max"
    MEAN = "mean"
    ZERO = "zero"
    ONE = "one"
