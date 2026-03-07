# Use of popups/modals in the GSO system

## Where we use modals

- **Notifications**: Single dropdown (Facebook-style): scrollable list of notifications (up to 50) with “Mark all as read” at the bottom. No “See all” link; users scroll inside the dropdown. Standalone notifications pages remain for direct links.
- **New request**: Unit selection and request form open in modals from the dashboard (requestor).
- **View details (requestor)**: Clicking “View Details” on a request in “My Requests” opens the request detail in a modal instead of a separate page.
- **Profile & settings**: Profile view and edit form in a modal (requestor).
- **Feedback (CSM)**: Feedback form opens in a modal on the request detail (requestor).

## Is this a good approach?

**Yes, when used as we do** — for quick actions and read-only or short forms without losing context.

### Benefits

1. **Context kept**: User stays on the dashboard or list; no full-page navigation for “peek” actions (see all notifications, view one request).
2. **Fewer page loads**: Faster for “See all notifications” and “View details”; feels lighter.
3. **Clear primary flow**: Dashboard remains the main screen; modals support secondary tasks (new request, profile, feedback).
4. **Full page still available**: “View full page” in the detail modal and standalone URLs (e.g. `/requestor/notifications/`) allow direct links, bookmarking, and printing when needed.

### When to avoid modals

- **Long workflows**: Multi-step flows are often better as full pages (e.g. staff request management with assign/approve/WAR).
- **Primary content**: The main thing the user came to do should usually be the page, not a popup.
- **Complex forms**: Very long or complex forms (e.g. WAR, reports) stay as full pages for clarity and accessibility.

### Summary

Using modals for **“see all” lists, quick view details, and short forms** (new request, profile, feedback) is a good fit for this system. We keep full-page URLs where they add value (notifications page, request detail) and use modals to reduce navigation and keep the user in context. For staff-side request handling and long forms we keep full-page flows. This balance is a sound approach.
