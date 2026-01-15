from ledger.models import Voucher, VoucherEntry


def test_voucher_is_balanced():
    voucher = Voucher(
        entries=[
            VoucherEntry(account_code="1001", debit_amount=1000),
            VoucherEntry(account_code="2001", credit_amount=1000),
        ]
    )
    assert voucher.is_balanced()


def test_voucher_not_balanced():
    voucher = Voucher(
        entries=[
            VoucherEntry(account_code="1001", debit_amount=1000),
            VoucherEntry(account_code="2001", credit_amount=900),
        ]
    )
    assert not voucher.is_balanced()
