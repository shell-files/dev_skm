from jobs.core.utils import clearJsonl
from jobs.core.paths import (
    trainCsv,
    trainJsonl,
    errorCsv
)


def step00():
    clearJsonl(trainJsonl)
