class Age:
    DAYS_IN_YEAR = 112

    def __init__(self, years: int = 0, days: int = 0):
        """
        Initialize Age with years and days.
        Days should be < 112; if not, it rolls over automatically.
        """
        total_days = years * self.DAYS_IN_YEAR + days
        self.years, self.days = divmod(total_days, self.DAYS_IN_YEAR)

    def add_days(self, days: int):
        """
        Increase age by a certain number of days.
        """
        total_days = self.to_days() + days
        self.years, self.days = divmod(total_days, self.DAYS_IN_YEAR)

    def add_years(self, years: int):
        """
        Increase age by a certain number of years.
        """
        self.years += years

    def to_days(self) -> int:
        """
        Convert age to total days.
        """
        return self.years * self.DAYS_IN_YEAR + self.days

    def get_age(self) -> float:
        """
        Get age as a float (years + fraction of year).
        """
        return self.years + self.days / self.DAYS_IN_YEAR

    def __str__(self):
        return f"{self.years} years and {self.days} days"

    def __repr__(self):
        return f"Age(years={self.years}, days={self.days})"
