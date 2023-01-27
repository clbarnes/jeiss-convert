import datetime as dt
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from datetime_matcher import DatetimeMatcher

from .misc import DATE_FORMAT


def datetime_from_path(dat_path: Path, datetime_pattern: str) -> dt.datetime:
    """Infer a .dat file's acquisition datetime from its path.

    More information about dfregex can be found here:
    https://github.com/stephen-zhao/datetime_matcher#dfregex-syntax-informal-spec

    The given pattern does not have to be a complete match for the path,
    although if there is a risk of multiple matches,
    the more specific the better.

    Parameters
    ----------
    dat_path : Path
    datetime_pattern : str
        Dfregex, i.e. regex plus C-like date/time codes,
        used to select datetime from stringified file path.

    Returns
    -------
    dt.datetime
        Inferred acquisition date.

    Raises
    ------
    ValueError
        Any number but 1 unique datetime detected in path.
    """
    dtm = DatetimeMatcher()
    datetimes = set(dtm.extract_datetimes(datetime_pattern, str(dat_path)))

    if len(datetimes) != 1:
        raise ValueError(
            f"Cannot match datetime, {len(datetimes)} options found "
            "for pattern '{datetime_pattern}' in path '{dat_path}'"
        )

    return datetimes.pop()


def get_csv_metadata(
    meta_df: pd.DataFrame,
    datetime: dt.datetime,
) -> dict[str, Any]:
    """Find metadata from a row of a CSV based on acquisition date.

    Parameters
    ----------
    meta_df : pd.DataFrame
        DataFrame representing metadata CSV.
        Must have string "Date" and "Time" columns with formats
        ``%d/%m/%Y`` and ``%H:%M:%S`` respectively.
    datetime : dt.datetime
        Acquisition datetime, used to find correct entry.

    Returns
    -------
    dict[str, Any]
        Mapping from column name to value for the appropriate row.
        An additional value with key ``"Datetime__iso"`` will be included,
        containing the ISO-8601 datetime string.

    Raises
    ------
    ValueError
        Cannot find exactly 1 row matching the given datetime.
    """
    date_str = datetime.strftime(DATE_FORMAT)
    time_str = datetime.strftime("%H:%M:%S")

    datetime_str = datetime.isoformat(sep=" ")

    row_idx = np.logical_and(
        meta_df["Date"] == date_str,
        meta_df["Time"] == time_str,
    )

    if row_idx.sum() != 1:
        raise ValueError("%s CSV rows matching .dat datetime found")

    subdf = meta_df.loc[row_idx]

    d = {col: subdf[col].to_numpy()[0] for col in subdf.columns}
    d["Datetime__iso"] = datetime_str

    return d
