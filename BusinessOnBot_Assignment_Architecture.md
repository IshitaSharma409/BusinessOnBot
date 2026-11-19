# BusinessOnBot Product Intern Assignment

## Step-by-Step Architecture: Preventing Unsafe AI Commitments

### 1. Problem framing

A **promise** is a statement that makes a customer reasonably believe an
outcome, action, price, availability, safety claim, or exception is
confirmed.

Examples: - "Your refund will arrive tomorrow" --- a time commitment. -
"It is in stock" --- an availability claim. - "Use SAVE20" --- a
discount/price commitment. - "This is completely safe during pregnancy"
--- a health/safety assurance. - "You can return it after 15 days" --- a
policy exception.

A helpful answer explains what is known and what the customer can do
next. A commitment confirms an outcome that must be supported by
reliable, current data or an authorised business rule.

**Who can be harmed:** customers (wrong expectations, financial or
safety harm), brands (cost, complaints and loss of trust), and
BusinessOnBot (product reliability and reputation).

**Measure the problem:** track unsupported-commitment rate: the
percentage of audited agent replies containing a commitment not
supported by an approved source or action result. Also tag severity and
category.

### 2. Assumptions to validate

  -----------------------------------------------------------------------
  Assumption                          How to test it
  ----------------------------------- -----------------------------------
  Brand policies, catalogue,          Audit sample integrations; check
  inventory and order data can be     missing, stale and conflicting
  retrieved with source and freshness records.
  information.                        

  Some actions (refund initiation,    Map each brand's permissions and
  discount creation, return approval) approval rules.
  require brand authorisation.        

  The same safety checks can run      Replay the same test cases through
  across all channels.                WhatsApp, Instagram, Messenger,
                                      email, voice and web chat.

  A response can be checked before it Measure added latency and confirm
  reaches the customer.               every channel uses the shared
                                      response gateway.

  High-risk topics need stricter      Review historical conversations
  evidence than ordinary product      with brand/support teams and label
  FAQs.                               risk levels.

  Human support is available for      Confirm escalation hours, queues,
  unresolved or high-risk cases.      ownership and service-level
                                      expectations.
  -----------------------------------------------------------------------

These are working assumptions, not confirmed facts about BusinessOnBot's
current systems.

### 3. Proposed architecture

``` text
Customer message
      |
      v
Channel adapter (WhatsApp / Instagram / Messenger / Email / Voice / Web)
      |
      v
Shared conversation + intent/risk detection
      |
      v
Retrieve approved evidence
(policies, catalogue, inventory, order/refund status, authorised promotions)
      |
      v
AI drafts a response
      |
      v
Commitment & policy guardrail
- Is there evidence for each factual claim?
- Is the data current and for this customer/order?
- Is this action permitted?
- Is the topic high risk?
      |
      +---------------------+-----------------------+
      |                     |                       |
      v                     v                       v
   ALLOW                 REWRITE                 BLOCK / ESCALATE
 grounded answer      remove unsupported       no definitive answer;
                      commitment; explain      route to human if needed
                      uncertainty/next step
      |                     |                       |
      +---------------------+-----------------------+
                            |
                            v
                 Send response to channel
                            |
                            v
               Log evidence, decision and outcome
                            |
                            v
                 Audit, feedback and monitoring
```

**Key design principle:** do not rely on the model's confidence or
prompt instructions alone. The guardrail is a separate validation step
between the AI draft and the customer. It should use the same rules
regardless of channel.

### 4. Decision flow and refund example

**Customer:** "Where is my refund? I returned the kurta 6 days ago."

1.  Identify intent as `refund_status` and mark it as a
    financial/time-commitment risk.
2.  Retrieve the order, return and refund records using the customer's
    verified order identity.
3.  Check whether the return was received, refund was initiated, and an
    estimated completion date is explicitly available from a trusted
    system.
4.  Compare the AI draft with the retrieved evidence.
5.  Choose an action:
    -   **Allow** only if the refund status and any stated date are
        supported by current records.
    -   **Rewrite** if the status is known but no confirmed arrival date
        exists. Example: "Your return is recorded. I can't confirm the
        refund arrival date yet. Our support team can check the latest
        status."
    -   **Block and escalate** if records are missing, contradictory,
        belong to another order, or indicate an exception requiring
        approval.
6.  Log the original draft, evidence used, guardrail decision and final
    response.

For the original reply --- "Your refund has been processed and will
reach your account by tomorrow" --- block that wording unless both
processing and the arrival estimate are verified. If only processing is
verified, rewrite to state only that fact.

### 5. What each guardrail does

-   **Allow:** low-risk or high-risk claims that have the required
    approved evidence and permissions.
-   **Rewrite:** useful answer is possible, but the draft overstates
    certainty. Remove the unsupported claim and provide a safe next
    step.
-   **Block / escalate:** no reliable evidence, conflicting data,
    unauthorised exception, or a high-risk question that requires a
    qualified human.
-   **Warn:** notify an internal reviewer when a near-miss or repeated
    risky pattern is detected; a warning alone should not allow an
    unsupported promise to reach the customer.
-   **Log:** record every decision for audit, debugging and measurement.
    Logging does not replace blocking or rewriting.

### 6. Ownership and customer recovery

-   **Brand:** owns the accuracy of its policies, catalogue, inventory,
    order data and approval rules.
-   **BusinessOnBot:** owns the guardrail design, integration checks,
    monitoring, escalation controls and incident response.
-   **AI model:** is a component, not the accountable owner. Its output
    must be validated before delivery.

If a customer was already told "tomorrow": 1. Check the actual refund
status immediately. 2. If the date is unsupported or wrong, contact the
customer proactively and apologise. 3. Explain the verified status
without inventing a replacement date. 4. Route the case to the brand's
support team for resolution and follow-up. 5. Record the incident,
impact and root cause; fix the data, rule or guardrail that failed.

### 7. Where the solution can break

  -----------------------------------------------------------------------
  Failure case            Risk                    Mitigation
  ----------------------- ----------------------- -----------------------
  Order or inventory data The system confidently  Check timestamps/TTL;
  is stale.               repeats outdated        treat stale data as
                          information.            unavailable and
                                                  escalate or qualify the
                                                  answer.

  Brand policy conflicts  A generic rule gives    Apply order-specific
  with an individual      the wrong answer.       authorised decisions;
  order exception.                                escalate unresolved
                                                  conflicts.

  Product name, size or   Agent confirms the      Ask a clarifying
  colour is ambiguous.    wrong variant or stock. question and verify the
                                                  exact SKU/variant
                                                  before confirming.

  Customer asks a         Unsupported advice      Do not make a safety
  medical/safety          could cause harm.       guarantee; provide
  question, such as                               approved product
  pregnancy suitability.                          information and direct
                                                  the customer to a
                                                  qualified professional.

  Guardrail is too strict Customer experience     Use risk-based
  and blocks ordinary     becomes slow or         thresholds, safe
  helpful replies.        frustrating.            rewrites and review
                                                  false positives.

  Human support is        Escalated cases remain  Acknowledge the
  unavailable.            unresolved.             handoff, create a
                                                  ticket, provide a
                                                  realistic follow-up
                                                  expectation only if
                                                  supported, and track
                                                  the queue.
  -----------------------------------------------------------------------

### 8. Success metrics and safe rollout

**Primary metric:** unsupported-commitment rate in audited
conversations. Target: reduce it substantially from the measured
baseline, with zero tolerance for severe unsupported safety or financial
commitments.

**Backfire metric:** safe-response usefulness rate (or unnecessary-block
rate). Monitor whether the agent is refusing or escalating questions it
could have answered safely.

**Rollout plan:** 1. Build a labelled evaluation set from the five
assignment examples plus real, anonymised edge cases across all
channels. 2. Run the guardrail in shadow mode: score drafts and log
decisions without changing customer replies. 3. Review false positives
and false negatives with brand/support teams; refine rules and evidence
requirements. 4. Enable rewrite/block for high-risk categories with a
small pilot brand and limited traffic. 5. Expand channel by channel only
after quality, latency and escalation performance meet agreed
thresholds. 6. Monitor metrics and incidents continuously; keep a
rollback switch.

### 9. Final recommendation

Build a **shared, evidence-based response guardrail** after AI
generation and before delivery. Make commitments only when supported by
fresh, customer-specific data and authorised rules. Otherwise rewrite
the answer to be transparent, or block and escalate when the risk is
high. This addresses the root problem across every channel instead of
relying only on better prompting.
