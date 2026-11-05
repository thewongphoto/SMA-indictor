"""Calendar tick placement with measured, non-overlapping labels."""
from dataclasses import dataclass
from datetime import date
import math


@dataclass(frozen=True)
class DateTick:
    index: int
    label: str
    center: float
    width: float


def date_ticks(dates,start,end,width,measure,gap=12):
    if not dates or width <= 0:
        return ()
    first,last = max(0,math.ceil(start)),min(len(dates)-1,math.floor(end))
    if first > last:
        return ()
    months,years,previous_month,previous_year = [],[],None,None
    for index in range(first,last+1):
        day = date.fromisoformat(dates[index])
        month = day.year*12+day.month-1
        if month != previous_month:
            months.append((index,day,month))
            previous_month = month
        if day.year != previous_year:
            years.append((index,day,day.year))
            previous_year = day.year

    def layout(candidates,stride,monthly):
        origin = candidates[0][2]
        chosen = [item for item in candidates if (item[2]-origin)%stride==0]
        placed = []
        for index,day,_ in chosen:
            label = day.strftime("%b %Y") if monthly else str(day.year)
            size = measure(label)
            if size > width:
                return None
            x = (index-start)/max(1,end-start)*width
            center = max(size/2,min(width-size/2,x))
            if placed and center-size/2 < placed[-1].center+placed[-1].width/2+gap:
                return None
            placed.append(DateTick(index,label,center,size))
        return tuple(placed)

    for stride in (1,2,3,4,6):
        ticks = layout(months,stride,True)
        if ticks is not None and (len(ticks)>=2 or len(months)==1):
            return ticks
    for stride in (1,2,3,5,10,20,50,100,200):
        ticks = layout(years,stride,False)
        if ticks:
            return ticks
    return ()
