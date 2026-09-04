# Plan

Answer each of these, in your own words.

- How did you break the work into sessions?
 >I worked in short sessions of about an hour to ninety minutes, spread across most days of the week instead of one long sitting, so I could come back with a clear head and catch things I'd missed. But due to some issue with my pc i lost the loaclly made files so have to remake from what i had on github again in one day. 

- What order did you build in, and why that order?
 >Accounts and roles first, since everything else depends on knowing if someone's an editor or a writer. Then sections, since articles need somewhere to belong. Then the article model and lifecycle, the most complicated part, once everything underneath it was solid. Search, filters and pagination came next, then bulk actions and the CSV export since those reuse the same querying logic. Dashboard and overdue alerts came last, since both are just different views over data that already existed.
 
- What did you estimate versus what it actually took?
 >I underestimated the article lifecycle by a lot. It looked like a status field with a few moves at first, but working through every rule in the brief took much longer once I actually hit the edge cases. The dashboard and CSV export went the other way, faster than expected since the queries underneath already existed.

- What did you cut when you ran short?
 >I got through all ten required goals, nothing from the core brief got dropped. The stretch ideas, like a revision diff or a style guide checklist, I skipped, since I'd rather have all ten goals solid than extras with less testing behind them.
