from django.db import models
from datetime import datetime


class PublicContract(models.Model):

    created_at = models.DateTimeField(default=datetime.utcnow)
    updated_at = models.DateTimeField(auto_now=True)

    region_id = models.BigIntegerField()
    buyout = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    collateral = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    contract_id = models.BigIntegerField(unique=True)
    date_expired = models.DateTimeField()
    date_issued = models.DateTimeField()
    days_to_complete = models.IntegerField(null=True)
    end_location_id = models.BigIntegerField(null=True)
    for_corporation = models.BooleanField(null=True)
    issuer_corporation_id = models.BigIntegerField()
    issuer_id = models.BigIntegerField()
    price = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    reward = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    start_location_id = models.BigIntegerField(null=True)
    title = models.CharField(max_length=1024, null=True)
    type = models.CharField(max_length=255)
    volume = models.FloatField(null=True)


class PublicContractItem(models.Model):

    created_at = models.DateTimeField(default=datetime.utcnow)

    contract = models.ForeignKey(PublicContract, on_delete=models.CASCADE)

    is_blueprint_copy = models.BooleanField(null=True)
    is_included = models.BooleanField()
    item_id = models.BigIntegerField(null=True)
    material_efficiency = models.IntegerField(null=True)
    quantity = models.IntegerField()
    record_id = models.BigIntegerField()
    runs = models.IntegerField(null=True)
    time_efficiency = models.IntegerField(null=True)
    type_id = models.BigIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "contract",
                    "record_id",
                ],
                name="unique_contract_record_id",
            )
        ]