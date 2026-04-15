from django.contrib.auth import get_user_model

from stats.models import Test, Image, WBToken
from users.models import CustomUser


def create_user(_id: int) -> CustomUser:
    User = get_user_model()

    return User.objects.create_user(
        email=f"test_user_{_id}@test.com",
        password="123",
    )

def create_test(
    user: CustomUser,
    name: str,
    wb_token: WBToken,
    impressions_per_cycle=100,
    max_impressions_per_image=1000,
    time_per_cycle=60,
) -> Test:
    return Test.objects.create(
        user=user,
        wb_token=wb_token,
        campaign_id=1,
        product_id=1,
        name=name,
        impressions_per_cycle=impressions_per_cycle,
        max_impressions_per_image=max_impressions_per_image,
        time_per_cycle=time_per_cycle,
    )

def create_image(test: Test, position: int) -> Image:
    return Image.objects.create(
        test=test,
        position=position,
        image="image.jpg"
    )

def create_wb_token(user, token: str = None) -> WBToken:
    return WBToken.objects.create(
        user=user,
        token=token or f"token_{user.id}_{WBToken.objects.count()}"
    )
