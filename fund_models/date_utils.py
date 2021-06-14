import calendar
import datetime
from typing import List


def year_month_num(date: datetime.date) -> int:
    '''
    Returns the year part of date multiplied by 12 plus the month number.
    '''
    return date.year * 12 + date.month

def end_of_month_from_date(date: datetime.date) -> datetime.date:
    '''
    Returns the last day of the month, of the month of the date.
    '''
    year_month_int = year_month_num(date)
    eom = end_of_month_from_int(year_month_int)
    return eom

def end_of_month_from_int(year_month_int: int) -> datetime.date:
    '''
    Returns the last day of the month, of the month of the date.
    '''    
    if year_month_int % 12 != 0:
        eom_year = year_month_int // 12
        eom_month = year_month_int % 12
    else:
        eom_year = year_month_int // 12 - 1
        eom_month = 12
    eom_day = calendar.monthrange(eom_year, eom_month)[1]
    eom = datetime.date(eom_year, eom_month, eom_day)
    return eom

def add_n_months(start_date: datetime.date, num_months: int, end_of_month: bool = True) -> datetime.date:
    '''
    Returns a date incremented by the number of monthly intervals specified.
    
    Where the return date is a month with more days than the start date,
    the boolean end_of_month flag determines whether to return the same
    day number of the start date or the end of the month rather.
    '''   
    return_date_year_month_int = year_month_num(start_date) + num_months

    if return_date_year_month_int % 12 != 0:
        return_date_year = return_date_year_month_int // 12
        return_date_month = return_date_year_month_int % 12
    else:
        return_date_year = return_date_year_month_int // 12 - 1
        return_date_month = 12

    return_date_day = min(start_date.day, calendar.monthrange(return_date_year, return_date_month)[1])
    
    return_date = datetime.date(return_date_year, return_date_month, return_date_day)

    if end_of_month:
        return end_of_month_from_date(return_date)
    else:
        return return_date

def number_of_months_diff(start_date: datetime.date, end_date: datetime.date) -> int:
    '''
    Returns the number of months difference between two dates.
    '''
    month_diff = year_month_num(end_date) - year_month_num(start_date)
    return month_diff

def generate_monthly_date_series(start_date: datetime.date, end_date: datetime.date) -> List[datetime.date]:
    '''
    Returns a list of end of month dates between two dates.

    The list includes the end of the month of both the start and end date.
    '''
    month_diff = number_of_months_diff(start_date, end_date)
    dates = [end_of_month_from_int(year_month_num(start_date) + diff) for diff in range(0, month_diff + 1)]
    return dates

def days_in_month(date: datetime.date) -> int:
    '''
    Returns the number of days in a month.
    '''
    return calendar.monthrange(date.year, date.month)[1]

def days_in_year(date: datetime.date) -> int:
    '''
    Returns the number of days in a year.
    '''
    return (datetime.date(date.year + 1, 1, 1) -  datetime.date(date.year, 1, 1)).days