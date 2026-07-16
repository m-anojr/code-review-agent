class UserProfile:
    def __init__(self, data: dict):
        self.name = data.get("name")
        self.address = data.get("address")

    def get_city(self):
        # bug: self.address could be None, accessing .get on None raises AttributeError
        return self.address.get("city", "Unknown")

    def get_display_name(self):
        # bug: self.name could be None, calling .upper() on None raises AttributeError
        return self.name.upper()

    def get_postal_code(self):
        # safe version for comparison
        if self.address:
            return self.address.get("postal_code", "")
        return ""
