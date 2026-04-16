from django.db.models import F, Sum
from stats.models import Test, ImageShowStat


def run_ctr(test: Test, cycle_number: int):
    print(f"\nCTR Test {test.id} | cycle={cycle_number}")

    stats = list(
        ImageShowStat.objects
        .filter(
            test=test,
            cycle_number=cycle_number,
            finished_at__isnull=False  # только завершённые
        )
        .values("image_id")
        .annotate(
            total_views=Sum(F("end_views") - F("start_views")),
            total_clicks=Sum(F("end_clicks") - F("start_clicks")),
        )
    )

    stats_by_image = {
        row["image_id"]: {
            "views": row["total_views"] or 0,
            "clicks": row["total_clicks"] or 0,
        }
        for row in stats
    }

    best_image_id = None
    best_ctr = -1

    images = list(test.images.order_by("position").values("id"))
    for image in images:
        image_id = image["id"]
        views = stats_by_image.get(image_id, {}).get("views", 0)
        clicks = stats_by_image.get(image_id, {}).get("clicks", 0)
        ctr = (clicks / views) if views else 0.0

        print(
            f"Image {image_id} | "
            f"views={views} "
            f"clicks={clicks} "
            f"CTR={ctr:.3f}"
        )

        if views > 0 and ctr > best_ctr:
            best_ctr = ctr
            best_image_id = image_id

    if best_image_id:
        from stats.models import Image

        best_image = Image.objects.get(id=best_image_id)
        best_image.wins_count += 1
        best_image.save(update_fields=["wins_count"])

        print(f"🏆 BEST → Image {best_image.id} | CTR={best_ctr:.3f}")
    else:
        print("🏆 BEST → не определен (нет показов в закрытом цикле)")
