import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from coop.models import MemberOrder, OrderItem  # Replace 'your_app' with the actual name of your app
from product.models import Item, Product, ProductVariation
from coop.models import MemberOrder, CooperativeMember, OrderItem, Collection
from coop.forms import OrderItemForm, MemberOrderForm
from coop.views.member import save_transaction
from conf.utils import generate_alpanumeric, genetate_uuid4, log_error, log_debug, generate_numeric, float_to_intstring, get_deleted_objects,\
get_message_template as message_template
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand, CommandError
from conf.utils import generate_numeric
from coop.models import CooperativeMember
from conf.utils import generate_numeric



class Command(BaseCommand):
    help = 'Create an order for a given item'

    def add_arguments(self, parser):
        parser.add_argument('item_name', type=str, help='Name of the item for the order')
        parser.add_argument('count', type=str, help='Name of the item for the order')

    def handle(self, *args, **kwargs):
        item_name = kwargs['item_name']
        count = kwargs['count']

        # Assuming you want to get the first user as the creator of the order
        user = User.objects.first()

        # Check if the item exists
        try:
            item = ProductVariation.objects.get(name=item_name)
        except Item.DoesNotExist:
            self.stdout.write(self.style.ERROR("Item with name '%s' does not exist." % item_name))
            return

        # member = CooperativeMember.objects.filter(id__gte=52, id__lte=100)
        member = CooperativeMember.objects.filter(cooperative__id=1)
        # Check if there are at least 126 records
        if members.count() >= count:
            # Get 126 random records
            random_members = random.sample(list(members), count)
        else:
            # Handle case where there are not enough records
            print("Error: There are not enough records.")
        count = 1
        for m in random_members:
            # Create MemberOrder
            order_date = self.generate_random_july_date()
            member_order = MemberOrder.objects.create(
                cooperative=m.cooperative,  # Adjust accordingly based on your model structure
                member=m,  # Adjust accordingly based on your model structure
                order_reference=generate_numeric(8, '30'),
                order_price=0,
                request_type='CASH',  # Adjust accordingly
                status='SUCCESSFUL',
                order_date=order_date,  # Import timezone from django.utils
                created_by=user,
            )

            random_number = random.randint(10, 250)
            total = random_number * item.price

            # Create OrderItem
            order_item = OrderItem.objects.create(
                order=member_order,
                item=item,
                quantity=random_number,  # Adjust accordingly
                unit_price=item.price,  # Assuming you have a default_price field in your Item model
                price=total,  # Assuming you have a default_price field in your Item model
                status='SUCCESSFUL',
                created_by=user,
            )
            member_order.order_price = total
            member_order.save()
            count += 1
            self.stdout.write(self.style.SUCCESS("Order for  created successfully. %s" % count))

    def generate_random_july_date(self):
        start_date = datetime(year=2023, month=12, day=1)  # Adjust the year as needed
        end_date = datetime(year=2024, month=2, day=20)  # Adjust the year as needed
        random_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
        return timezone.make_aware(random_date, timezone.get_current_timezone())

