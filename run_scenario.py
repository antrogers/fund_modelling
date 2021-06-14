import datetime
import os

import pandas as pd

from fund_models.fund_models import ClosedEndFund


funds = [
    ClosedEndFund(
                fund_name = 'Fund1',
                fund_start_date = datetime.date(2021, 3, 31),
                deployment_start_date = datetime.date(2021, 6, 30),
                number_of_months_of_deployment=36,
                number_of_months_in_between_deployments=3,
                length_of_deployment_in_months=36,
                annual_effective_irr = 0.15,
                annual_effective_irr_hurdle=0.1,
                committed_capital = 500000000,
                annual_mgmt_fee_rate = 0.005,
                carry_percent = 0.2,
                carry_catch_up = True
            ),
    ClosedEndFund(
                fund_name = 'Fund2',
                fund_start_date = datetime.date(2024, 3, 31),
                deployment_start_date = datetime.date(2024, 6, 30),
                number_of_months_of_deployment=36,
                number_of_months_in_between_deployments=3,
                length_of_deployment_in_months=36,
                annual_effective_irr = 0.15,
                annual_effective_irr_hurdle=0.1,
                committed_capital = 600000000,
                annual_mgmt_fee_rate = 0.005,
                carry_percent = 0.2,
                carry_catch_up = True
            ),
    ClosedEndFund(
                fund_name = 'Fund3',
                fund_start_date = datetime.date(2024, 3, 31),
                deployment_start_date = datetime.date(2024, 6, 30),
                number_of_months_of_deployment=24,
                number_of_months_in_between_deployments=1,
                length_of_deployment_in_months=36,
                annual_effective_irr = 0.12,
                annual_effective_irr_hurdle=0.1,
                committed_capital = 200000000,
                annual_mgmt_fee_rate = 0.005,
                carry_percent = 0.2,
                carry_catch_up = False
            ),
    ClosedEndFund(
                fund_name = 'Fund4',
                fund_start_date = datetime.date(2024, 3, 31),
                deployment_start_date = datetime.date(2024, 6, 30),
                number_of_months_of_deployment=24,
                number_of_months_in_between_deployments=1,
                length_of_deployment_in_months=36,
                annual_effective_irr = 0.2,
                annual_effective_irr_hurdle=0.1,
                committed_capital = 200000000,
                annual_mgmt_fee_rate = 0.005,
                carry_percent = 0.2,
                carry_catch_up = False
            )
]

fund_schedules_df = pd.concat([fund.generate_fund_schedules_summary_df() for fund in funds])
fund_inputs_df = pd.concat([fund.generate_fund_inputs_summary_df() for fund in funds])

try:
    os.remove('power_bi_datasets/fund_schedules.csv')
except:
    pass

try:
    os.remove('power_bi_datasets/fund_inputs.csv')
except:
    pass

fund_schedules_df.to_csv('power_bi_datasets/fund_schedules.csv', index_label='date')
fund_inputs_df.to_csv('power_bi_datasets/fund_inputs.csv', index=False)

with open('power_bi_datasets/path_for_power_bi.txt', 'w') as path_for_power_bi:
    path_for_power_bi.write(os.getcwd())



