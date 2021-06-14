import calendar
import datetime
import os
from typing import List, Dict

import pandas as pd
import numpy_financial as npf

from fund_models.date_utils import (
    end_of_month_from_date,
    generate_monthly_date_series, 
    add_n_months,
    days_in_month,
    days_in_year
)

#exception classes

class ClosedEndFundError(Exception):
    def __init__(self, message: str):
        super().__init__(message)

#fund classes

class ClosedEndFund():

    def __init__(self,
            fund_name,
            fund_start_date,
            deployment_start_date,
            annual_effective_irr,
            committed_capital,
            annual_mgmt_fee_rate, 
            carry_percent,
            annual_effective_irr_hurdle,
            number_of_months_of_deployment=36,
            number_of_months_in_between_deployments=3,
            length_of_deployment_in_months=36,
            carry_catch_up = True
        ) -> "ClosedEndFund":

        if fund_start_date > deployment_start_date:
            raise ClosedEndFundError('Deployment start date must be later than fund start date')

        if end_of_month_from_date(fund_start_date) != fund_start_date:
            raise ClosedEndFundError('Fund start date must be at end of month')

        if end_of_month_from_date(deployment_start_date) != deployment_start_date:
            raise ClosedEndFundError('Deployment start date must be at end of month')

        if number_of_months_of_deployment % number_of_months_in_between_deployments != 0:
            raise ClosedEndFundError(
                f'''
                The combination of {number_of_months_of_deployment} months in deployment \
                with {number_of_months_in_between_deployments} months in between deployments \
                generates {number_of_months_of_deployment / number_of_months_in_between_deployments} \
                deployments which is not allowed. There must be a whole number of deployments \
                else not all committed capital will be deployed.
                '''
            )

        if committed_capital <= 0:
            raise ClosedEndFundError('Committed capital must be greater than zero')

        self.fund_name = fund_name
        self.fund_start_date = fund_start_date
        self.annual_mgmt_fee_rate = annual_mgmt_fee_rate
        self.carry_percent = carry_percent
        self.fund_start_date = end_of_month_from_date(fund_start_date)
        self.deployment_start_date = end_of_month_from_date(deployment_start_date)
        self.annual_effective_irr = annual_effective_irr
        self.annual_effective_irr_hurdle = annual_effective_irr_hurdle
        self.committed_capital = committed_capital
        self.number_of_months_of_deployment = number_of_months_of_deployment
        self.number_of_months_in_between_deployments = number_of_months_in_between_deployments
        self.length_of_deployment_in_months = length_of_deployment_in_months
        self.carry_catch_up = carry_catch_up

    @property
    def monthly_date_series(self) -> List[datetime.date]:
        '''
        A complete schedule of month ends between the fund start date and last capital return.
        '''
        return generate_monthly_date_series(self.fund_start_date, max(self.generate_capital_returns()))

    @property
    def irr_per_month(self) -> float:
        '''
        Derived from the annual effective irr.
        '''
        return (1 + self.annual_effective_irr) ** (1/12) -1

    @property
    def irr_hurdle_per_month(self) -> float:
        '''
        Derived from the annual effective irr hurdle.
        '''
        return (1 + self.annual_effective_irr_hurdle) ** (1/12) -1

    def generate_deployments(self) -> Dict[datetime.date, float]:
        '''
        Returns a schedule of deployments.

        Deployments amounts and number of deployments are calculcated from fund arguments.        
        '''
        deployments = {}
        
        number_of_deployments = int(self.number_of_months_of_deployment / self.number_of_months_in_between_deployments)
        amount_per_deployment = self.committed_capital / number_of_deployments

        for num in range(0, number_of_deployments):
            deployments.update({
                add_n_months(self.deployment_start_date, num * self.number_of_months_in_between_deployments):
                amount_per_deployment
            })

        return deployments

    def generate_proceeds(self) -> Dict[datetime.date, float]:
        '''
        Returns a schedule of proceeds received by the fund that \
        is based on the deployments schedule.

        The timing is based on the length in deployment and \
        the amount received is calculated using the assumed annual_effective_irr \
        which is converted to an irr_per_month.     
        '''
        proceeds = {}
        for date, value in self.generate_deployments().items():
            amount = npf.fv(
                        rate=self.irr_per_month, 
                        nper=self.length_of_deployment_in_months, 
                        pmt=0, 
                        pv=-value, 
                        when='end'
                    )
            proceeds.update(
                {add_n_months(date, self.length_of_deployment_in_months): amount}
            )
        return proceeds

    def generate_capital_returns(self) -> Dict[datetime.date, float]:
        '''
        Returns a schedule of capital returns received by the fund that \
        is based on the deployments schedule.

        The timing is based on the length in deployment.    
        '''
        capital_returns = {}        
        for date, value in self.generate_deployments().items():
                capital_returns.update(
                    {add_n_months(date, self.length_of_deployment_in_months): value}
                )
        return capital_returns
    
    def generate_profits(self) -> Dict[datetime.date, float]:
        '''
        Returns a schedule of profits by month, which is calculated: \
        proceeds less capital return.
        '''
        profits = {}
        capital_returns = self.generate_capital_returns()
        for date, value in self.generate_proceeds().items():
            profit = value - capital_returns.get(date)
            profits.update({date: profit})
        return profits

    def calculate_total_profit(self) -> float:
        '''
        Sum of all profits, which for each month is calculated: proceeds less capital return.
        '''
        return sum(self.generate_profits().values())

    def generate_proceeds_allocations_as_dict(self) -> Dict[str, Dict[datetime.date, float]]:
        '''
        Returns multiple schedules that show how proceeds are to be allocated \
        between the limited and general partners.

        All proceeds are distributed to the limited partners until all deployed capital has been \
        repaid along with a hurdle return.

        Thereafter, if the general partner is entitled to a share in the preferred return \
        payments are shared equally between the general and limited partners until the general partner \
        has received an amount equal to their share of preferred return.

        Thereafter the general partner participates in proceeds based on the agreed carry, with \
        the balance allocated to the limited partners.        
        '''
        deployments = self.generate_deployments()
        proceeds = self.generate_proceeds()
        capital_returns = self.generate_capital_returns()

        lp_preferred_opening = {}        
        lp_preferred_irr_growth = {}
        lp_preferred_payments = {}
        lp_preferred_closing = {}

        catch_up_opening = {}
        catch_up_accruals = {}
        catch_up_payments_gp_share = {}
        catch_up_payments_lp_share = {}
        catch_up_closing = {}

        post_catch_up_payments_gp_share = {}
        post_catch_up_payments_lp_share = {}

        #cycle through each date and attribute profit shares
        for date in self.monthly_date_series:

            proceed = proceeds.get(date, 0)

            # first calculcate opening lp preferred balance (taking irr_hurdle into account)
            lp_preferred_opening_balance = lp_preferred_closing.get(add_n_months(date, -1), 0)
            lp_preferred_opening.update({date: lp_preferred_opening_balance})
            
            lp_preferred_irr_growth_for_month = lp_preferred_opening_balance * self.irr_hurdle_per_month
            lp_preferred_irr_growth.update({date: lp_preferred_irr_growth_for_month})
            
            deployment = deployments.get(date, 0)

            lp_preferred_payment = min(proceed, lp_preferred_opening_balance + lp_preferred_irr_growth_for_month + deployment)
            lp_preferred_payments.update({date: lp_preferred_payment})
            lp_preferred_closing.update({date: lp_preferred_opening_balance + lp_preferred_irr_growth_for_month + deployment - lp_preferred_payment})

            #catch opening and accrual
            catch_up_opening_balance = catch_up_closing.get(add_n_months(date, -1), 0)
            catch_up_opening.update({date: catch_up_opening_balance})

            #We must apply a fraction to the accrual so that the GP also shares in the carry catch up payments
            catch_up_accrual =  lp_preferred_irr_growth_for_month * (self.carry_percent / ( 0.5 - self.carry_percent) * 0.5) * self.carry_catch_up             
            catch_up_accruals.update({date: catch_up_accrual})

            # if lp preferred return is all paid, the GP is able to catch up performance fees
            # from the preferred return period (in agreed percentages)           
            if proceed > lp_preferred_payment:

                #catch up payment limited to balance
                catch_up_payment = min((catch_up_opening_balance + catch_up_accrual) / 0.5, proceed - lp_preferred_payment)       

                catch_up_payment_gp_share = catch_up_payment * 0.5
                catch_up_payment_lp_share = catch_up_payment * 0.5

                catch_up_payments_gp_share.update({date: catch_up_payment_gp_share})
                catch_up_payments_lp_share.update({date: catch_up_payment_lp_share})

                catch_up_closing.update({date: catch_up_opening_balance + catch_up_accrual - catch_up_payment_gp_share})

                # once the GP has caught up, perf fees are split in agreed proportions
                if proceed > lp_preferred_payment + catch_up_payment:
                    post_catch_up_payment = proceed - lp_preferred_payment - catch_up_payment

                    post_catch_up_payment_lp_share = post_catch_up_payment * (1 - self.carry_percent)
                    post_catch_up_payment_gp_share = post_catch_up_payment * self.carry_percent

                    post_catch_up_payments_gp_share.update({date: post_catch_up_payment_gp_share})
                    post_catch_up_payments_lp_share.update({date: post_catch_up_payment_lp_share})

                else:
                    post_catch_up_payments_gp_share.update({date: 0})
                    post_catch_up_payments_lp_share.update({date: 0})

            else:
                # lp_preferred is still being paid, therefore accrue catch up regularly
                catch_up_closing.update({date: catch_up_opening_balance + catch_up_accrual})

                catch_up_payments_gp_share.update({date: 0})
                catch_up_payments_lp_share.update({date: 0})
                
                post_catch_up_payments_gp_share.update({date: 0})
                post_catch_up_payments_lp_share.update({date: 0})   

        schedules = {

            "lp_preferred_opening": lp_preferred_opening,
            "lp_preferred_irr_growth": lp_preferred_irr_growth,
            "lp_preferred_payments": lp_preferred_payments,
            "lp_preferred_closing": lp_preferred_closing,
            "catch_up_opening": catch_up_opening,
            "catch_up_accruals": catch_up_accruals,
            "catch_up_payments_gp_share": catch_up_payments_gp_share,
            "catch_up_payments_lp_share": catch_up_payments_lp_share,
            "catch_up_closing": catch_up_closing,
            "post_catch_up_payments_gp_share": post_catch_up_payments_gp_share,
            "post_catch_up_payments_lp_share": post_catch_up_payments_lp_share
        }

        return schedules

    def generate_closing_invested_capital(self) -> Dict[datetime.date, float]:
        '''
        Returns a schedule of closing invested capital calculated.

        Closing invested capital is calculated: opening balance + deployment - capital return.
        '''
        closing_invested_capital = {}
        
        deployments = self.generate_deployments()
        capital_returns = self.generate_capital_returns()

        for date in self.monthly_date_series:
            opening_balance = closing_invested_capital.get(add_n_months(date, -1), 0)
            deployment = deployments.get(date, 0)
            capital_return = capital_returns.get(date, 0)
            closing_balance = opening_balance + deployment - capital_return        
            closing_invested_capital.update({date:closing_balance})
        
        return closing_invested_capital

    def generate_fee_paying_capital(self) -> Dict[datetime.date, float]:
        '''
        Returns a schedule of fee paying capital.

        Fees are calculated on commited capital until deployments cease, whereafter \
        fees are based on closing invested capital.
        '''
        fee_paying_capital = {}
        closing_invested_capital = self.generate_closing_invested_capital()
        last_deployments = max([k for k, v in self.generate_deployments().items()])

        for date in self.monthly_date_series:
            if date <= last_deployments:
                capital = self.committed_capital
            else:
                capital = closing_invested_capital.get(date, 0)        
                
            fee_paying_capital.update({date: capital})

        return fee_paying_capital

    def generate_mgmt_fees(self) -> Dict[datetime.date, float]:
        '''
        Returns a schedule of management fees.

        Fees are calculated on commited capital until deployments cease, whereafter \
        fees are based on closing invested capital.
        '''
        mgmt_fees = {}
        closing_invested_capital = self.generate_closing_invested_capital()
        last_deployments = max([k for k, v in self.generate_deployments().items()])

        for date in self.monthly_date_series:
            num_days_in_month = days_in_month(date)
            num_days_in_year = days_in_year(date)
            closing_invested_capital_balance = closing_invested_capital.get(date, 0)
                        
            if date <= last_deployments:
                fee = self.committed_capital * self.annual_mgmt_fee_rate \
                    * num_days_in_month / num_days_in_year
            else:
                fee = closing_invested_capital_balance * self.annual_mgmt_fee_rate \
                    * num_days_in_month / num_days_in_year
            
            mgmt_fees.update({date: fee})

        return mgmt_fees

    def generate_fund_inputs_summary_dict(self) -> Dict[str, any]:
        '''
        Returns all the attributes of the fund.
        '''
        return {
                "fund_name": self.fund_name,
                "fund_start_date": self.fund_start_date,
                "annual_mgmt_fee_rate": self.annual_mgmt_fee_rate,
                "carry_percent": self.carry_percent,
                "deployment_start_date": self.deployment_start_date,
                "number_of_months_of_deployment": self.number_of_months_of_deployment,
                "number_of_months_in_between_deployments": self.number_of_months_in_between_deployments,
                "length_of_deployment_in_months": self.length_of_deployment_in_months,
                "annual_effective_irr": self.annual_effective_irr,
                "annual_effective_irr_hurdle": self.annual_effective_irr_hurdle,
                "committed_capital": self.committed_capital,
                "carry_catch_up": self.carry_catch_up,
            }

    def generate_fund_schedules_summary_dict(self) -> Dict[str, Dict[datetime.date, float]]:
        '''
        Returns all the schedules related to the fund.
        '''
        schedules = {
            "dates": {date: date for date in self.monthly_date_series},
            "deployments": self.generate_deployments(),
            "capital_returns": self.generate_capital_returns(),
            "closing_invested_capital": self.generate_closing_invested_capital(),
            "fee_paying_capital": self.generate_fee_paying_capital(),
            "mgmt_fees": self.generate_mgmt_fees(),
            "proceeds": self.generate_proceeds(),
        }
        schedules.update(self.generate_proceeds_allocations_as_dict())

        return schedules

    def generate_fund_schedules_summary_df(self) -> pd.DataFrame:
        '''
        Returns all the schedules related to the fund.
        '''
        data_to_convert_to_df = self.generate_fund_schedules_summary_dict()
        sub_dfs = [pd.DataFrame.from_dict(data, orient='index', columns=[col_name]) for col_name, data in data_to_convert_to_df.items()]
        df = pd.concat(sub_dfs, axis=1).drop(columns=['dates'], axis=1)
        df['fund_name'] = self.fund_name
        return df.fillna(0)

    def generate_fund_inputs_summary_df(self) -> pd.DataFrame:
        '''
        Returns all the attributes of the fund.
        '''
        data_to_convert_to_df = self.generate_fund_inputs_summary_dict()
        df = pd.DataFrame(data_to_convert_to_df, index=[0])
        return df




        



