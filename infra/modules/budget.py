import datetime

import pulumi
from pulumi_azure_native import consumption

# TODO[SB]: make working
def create_budget(
    name: str,
    resource_group_name: pulumi.Output[str],
    subscription_id: str,
    owners: list,
    max_budget_amount: float = 1000,
    increment: float = 250
):
    number_of_increments = int(max_budget_amount / increment)
    notifications = {}
    for i in range(1, number_of_increments + 1):
        threshold_percentage = (increment * i) / max_budget_amount * 100
        notification_name = f"NotifyAt{int(increment * i)}"
        notifications[notification_name] = consumption.NotificationArgs(
            enabled=True,
            operator='GreaterThanOrEqualTo',
            threshold=threshold_percentage,
            contact_emails=owners,
            threshold_type='Actual'
        )

    budget = consumption.Budget(
        resource_name=name,
        budget_name=name,
        scope=pulumi.Output.concat(
            "/subscriptions/", subscription_id, "/resourceGroups/", resource_group_name
        ),
        amount=max_budget_amount,
        time_grain='Monthly',
        notifications=notifications,
        category='Cost',
        time_period=consumption.BudgetTimePeriodArgs(
            start_date=datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')  # Setting the start date to today
            # No end_date is specified for indefinite duration
        ),
        filter=consumption.BudgetFilterArgs(
            dimensions=consumption.BudgetComparisonExpressionArgs(
                name="ResourceGroupName",
                operator="In",
                values=[resource_group_name]
            )
        )
    )
    return budget
