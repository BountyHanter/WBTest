from django.db.models import Sum, F
from stats.models import Test, ImageShowStat


def run_ctr(test: Test):
    print(f"\nCTR Test {test.id} | cycle={test.current_cycle}")

    stats = (
        ImageShowStat.objects
        .filter(
            test=test,
            cycle_number=test.current_cycle,
            finished_at__isnull=False  # только завершённые
        )
        .values("image_id")
        .annotate(
            total_views=Sum(F("end_views") - F("start_views")),
            total_clicks=Sum(F("end_clicks") - F("start_clicks")),
        )
    )

    best_image_id = None
    best_ctr = -1

    for stat in stats:
        views = stat["total_views"]
        clicks = stat["total_clicks"]

        if not views:
            continue

        ctr = clicks / views

        print(
            f"Image {stat['image_id']} | "
            f"views={views} "
            f"clicks={clicks} "
            f"CTR={ctr:.3f}"
        )

        if ctr > best_ctr:
            best_ctr = ctr
            best_image_id = stat["image_id"]

    if best_image_id:
        from stats.models import Image

        best_image = Image.objects.get(id=best_image_id)
        best_image.wins_count += 1
        best_image.save(update_fields=["wins_count"])

        print(f"🏆 BEST → Image {best_image.id} | CTR={best_ctr:.3f}")