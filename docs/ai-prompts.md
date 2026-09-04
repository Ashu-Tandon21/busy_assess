# AI prompts

The prompts you actually used, in the order you used them, grouped by what you were trying to achieve. For each significant one: what you asked, what you got back, and what you had to correct.

Include at least one prompt that produced something wrong, and what you did about it.

If you did not use AI at all, say so here, and describe your process instead.

## <What you were trying to achieve>

### Prompt
> I asked Claude to help me build a signup page, and gave it the link to my GitHub repo so it could look at the actual codebase first.

### What you got
> Claude cloned the repo and pointed out that architecture.md already had a decision written down against public self signup, since the brief describes editors assigning writers rather than people signing themselves up. It asked whether I wanted public signup, an editor only add user flow, or wasn't sure. I picked editor only, since that matches the brief. It then built a form on Django's UserCreationForm, a create view gated behind the same EditorRequiredMixin used elsewhere, a roster list view, matching urls, and templates styled to match my existing sections pages. It also added a Team link to the nav for editors only, and tested that writers get blocked while editors can create an account.

### What you corrected
> What I first asked for would have meant a public registration form if taken literally, which clashed with what I'd already written in my own architecture doc. Claude flagged that before writing any code and asked me to pick a direction, which is why I didn't end up with something that contradicted the rest of the app. I also asked it not to push anything into my repo directly, so it gave me the files to copy in by hand instead.
