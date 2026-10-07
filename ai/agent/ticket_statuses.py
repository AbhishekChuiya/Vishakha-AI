TICKET_STATUS_IDS = {
    "NEW": [23],

    # OPEN is intentionally handled separately in the workflow
    # as includeClosed=False, meaning all active/non-closed tickets.

    "IN PROGRESS": [25],
    "PENDING": [26],
    "PENDING APPROVAL": [27],
    "RE-OPEN": [28],

    # Portal currently contains two Rejected status IDs.
    "REJECTED": [29, 37],

    "IN FULFILLMENT": [30],
    "FULFILLED": [31],
    "UNDER INVESTIGATION": [32],
    "USER INPUT REQUIRED": [33],
    "RESOLUTION PLANNING": [34],
    "USER INPUT PROVIDED": [35],
    "APPROVED": [36],
    "SCHEDULED": [38],
    "COMPLETED": [39],
    "FAILED": [40],
    "ON-HOLD": [41],
    "RESOLVED": [42],
    "CLOSED": [43],
    "CANCELLED": [44],

    "CR CREATED": [45],
    "CR PENDING FOR HOD APPROVAL": [46],
    "KDD - IN PROGRESS": [47],
    "KDD - UNDER REVIEW AT REQUESTER": [48],
    "KDD - UNDER HOD APPROVAL": [49],
    "KDD - APPROVED": [50],
    "EFFORT ESTIMATION UNDER IT APPROVAL": [51],
    "EFFORT ESTIMATION UNDER APPROVAL AT FC": [52],
    "CR APPROVED": [53],
    "DEVELOPMENT": [54],
    "TESTING": [55],
    "CR UNDER UAT": [56],
    "CR UNDER DEPLOYMENT": [57],
    "CR CLOSED": [58],
    "VISIT REQUIRED": [59],
    "UNDER UAT": [60],
}