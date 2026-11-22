SUBSCRIPTION_PLANS = {
    "STARTER": {
        "name": "Starter",
        "price": 89.99,
        "credits": 10,
        "guest_credits": 0,
        "priority": False,
    },
    "PREMIUM": {
        "name": "Premium",
        "price": 149.99,
        "credits": 20,
        "guest_credits": 2,
        "priority": False,
    },
    "UNLIMITED": {
        "name": "Unlimited",
        "price": 249.99,
        "credits": -1,
        "guest_credits": 5,
        "priority": True,
    },
}

PLAN_RANK = {"STARTER": 1, "PREMIUM": 2, "UNLIMITED": 3}
