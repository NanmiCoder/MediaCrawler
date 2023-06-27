import config


class PhonePool:
    """phone pool class"""

    def __init__(self):
        self.phones = []
        self.used_phones = set()

    def add_phone(self, phone):
        """add phone to the pool"""
        if phone not in self.phones:
            self.phones.append(phone)
            return True
        return False

    def remove_phone(self, phone):
        """remove phone from the pool"""
        if phone in self.used_phones:
            self.phones.remove(phone)
            self.used_phones.remove(phone)
            return True
        return False

    def get_phone(self):
        """get phone and mark as used"""
        if self.phones:
            left_phone = self.phones.pop(0)
            self.used_phones.add(left_phone)
            return left_phone
        return None

    def clear(self):
        """clear phone pool"""
        self.phones = []
        self.used_phones = set()


class IPPool:
    def __init__(self):
        self.ips = []
        self.used_ips = set()

    def add_ip(self, ip):
        """添加ip"""
        if ip not in self.ips:
            self.ips.append(ip)
            return True
        return False

    def remove_ip(self, ip):
        """remove ip"""
        if ip in self.used_ips:
            self.ips.remove(ip)
            self.used_ips.remove(ip)
            return True
        return False

    def get_ip(self):
        """get ip and mark as used"""
        if self.ips:
            left_ips = self.ips.pop(0)
            self.used_ips.add(left_ips)
            return left_ips
        return None

    def clear(self):
        """ clear ip pool"""
        self.ips = []
        self.used_ips = set()


class AccountPool:
    """account pool class"""

    def __init__(self):
        self.phone_pool = PhonePool()
        self.ip_pool = IPPool()

    def add_account(self, phone, ip):
        """add account to pool with phone and ip"""
        if self.phone_pool.add_phone(phone) and self.ip_pool.add_ip(ip):
            return True
        return False

    def remove_account(self, phone, ip):
        """remove account from pool """
        if self.phone_pool.remove_phone(phone) and self.ip_pool.remove_ip(ip):
            return True
        return False

    def get_account(self):
        """get account if no account, reload account pool"""
        phone = self.phone_pool.get_phone()
        ip = self.ip_pool.get_ip()
        if not phone or not ip:
            reload_account_pool(self)
            return self.get_account()
        return phone, ip

    def clear_account(self):
        """clear account pool"""
        self.phone_pool.clear()
        self.ip_pool.clear()


def reload_account_pool(apo: AccountPool):
    """reload account pool"""
    apo.clear_account()
    for phone, ip in zip(config.PHONE_LIST, config.IP_PROXY_LIST):
        apo.add_account(phone, ip)


def create_account_pool() -> AccountPool:
    """create account pool"""
    apo = AccountPool()
    reload_account_pool(apo=apo)
    return apo


if __name__ == '__main__':
    import time

    ac_pool = create_account_pool()
    p, i = ac_pool.get_account()
    while p:
        print(f"get phone:{p}, ip proxy:{i} from account pool")
        p, i = ac_pool.get_account()
        time.sleep(1)
