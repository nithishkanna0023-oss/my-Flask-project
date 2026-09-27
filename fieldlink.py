"""
Fieldlink Dispatch Console (Python)
====================================
Console version of the Service Link Provider, matching the three modules
of the web app:
    1. Overview     -> live stats + category breakdown + activity feed
    2. Technicians   -> roster management
    3. Requests      -> job queue, auto-linking, lifecycle

Run this file directly for an interactive text menu, or import
ServiceLinkProvider into your own code.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
import itertools


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ServiceCategory(Enum):
    PLUMBING = "Plumbing"
    ELECTRICAL = "Electrical"
    CARPENTRY = "Carpentry"
    APPLIANCE_REPAIR = "Appliance Repair"
    PAINTING = "Painting"
    CLEANING = "Cleaning"
    AC_REPAIR = "AC Repair"
    PEST_CONTROL = "Pest Control"


class RequestStatus(Enum):
    PENDING = "Pending"
    ASSIGNED = "Assigned"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Customer:
    customer_id: int
    name: str
    phone: str
    location: str


@dataclass
class Technician:
    technician_id: int
    name: str
    phone: str
    location: str
    skills: List[ServiceCategory]
    rating: float = 4.5
    is_available: bool = True
    jobs_completed: int = 0

    def has_skill(self, category: ServiceCategory) -> bool:
        return category in self.skills


@dataclass
class ServiceRequest:
    request_id: int
    customer: Customer
    category: ServiceCategory
    description: str
    created_at: datetime = field(default_factory=datetime.now)
    status: RequestStatus = RequestStatus.PENDING
    technician: Optional[Technician] = None

    def ticket_no(self) -> str:
        return f"#{self.request_id:04d}"

    def summary(self) -> str:
        tech = self.technician.name if self.technician else "Unassigned"
        return (f"[{self.ticket_no()}] {self.category.value} for "
                f"{self.customer.name} ({self.customer.location}) "
                f"-> {tech} | {self.status.value}")


@dataclass
class ActivityLogEntry:
    timestamp: datetime
    text: str


# ---------------------------------------------------------------------------
# Core provider
# ---------------------------------------------------------------------------

class ServiceLinkProvider:
    """Registers customers/technicians, links requests to the best-fit
    technician, and tracks stats for the Overview module."""

    def __init__(self, activity_limit: int = 8):
        self._customers: Dict[int, Customer] = {}
        self._technicians: Dict[int, Technician] = {}
        self._requests: Dict[int, ServiceRequest] = {}

        self._customer_ids = itertools.count(1)
        self._technician_ids = itertools.count(1)
        self._request_ids = itertools.count(1)

        self._activity: List[ActivityLogEntry] = []
        self._activity_limit = activity_limit

    def _log(self, text: str) -> None:
        self._activity.insert(0, ActivityLogEntry(datetime.now(), text))
        self._activity = self._activity[: self._activity_limit]

    # ---------------- Technicians module ----------------

    def register_technician(self, name: str, phone: str, location: str,
                             skills: List[ServiceCategory],
                             rating: float = 4.5) -> Technician:
        technician = Technician(next(self._technician_ids), name, phone,
                                 location, skills, rating)
        self._technicians[technician.technician_id] = technician
        self._log(f"{name} joined the roster "
                   f"({', '.join(s.value for s in skills)})")
        return technician

    def list_technicians(self, category: Optional[ServiceCategory] = None,
                          available_only: bool = False) -> List[Technician]:
        techs = list(self._technicians.values())
        if category:
            techs = [t for t in techs if t.has_skill(category)]
        if available_only:
            techs = [t for t in techs if t.is_available]
        return techs

    # ---------------- Requests module ----------------

    def register_customer(self, name: str, phone: str, location: str) -> Customer:
        customer = Customer(next(self._customer_ids), name, phone, location)
        self._customers[customer.customer_id] = customer
        return customer

    def create_request(self, customer: Customer, category: ServiceCategory,
                        description: str) -> ServiceRequest:
        request = ServiceRequest(next(self._request_ids), customer,
                                  category, description)
        self._requests[request.request_id] = request
        return request

    def find_best_technician(self, request: ServiceRequest) -> Optional[Technician]:
        """Must have the skill; prefer same location; then highest rating."""
        candidates = [
            t for t in self._technicians.values()
            if t.is_available and t.has_skill(request.category)
        ]
        if not candidates:
            return None
        candidates.sort(
            key=lambda t: (t.location != request.customer.location, -t.rating)
        )
        return candidates[0]

    def link(self, request: ServiceRequest) -> bool:
        technician = self.find_best_technician(request)
        if technician is None:
            request.status = RequestStatus.PENDING
            self._log(f"{request.ticket_no()} awaiting a technician")
            return False

        technician.is_available = False
        request.technician = technician
        request.status = RequestStatus.ASSIGNED
        self._log(f"{request.ticket_no()} linked to {technician.name}")
        return True

    def start_work(self, request: ServiceRequest) -> None:
        if request.status != RequestStatus.ASSIGNED:
            raise ValueError("Request must be ASSIGNED before work can start.")
        request.status = RequestStatus.IN_PROGRESS

    def complete_request(self, request: ServiceRequest) -> None:
        if request.technician:
            request.technician.is_available = True
            request.technician.jobs_completed += 1
            self._log(f"{request.ticket_no()} completed by {request.technician.name}")
        request.status = RequestStatus.COMPLETED

    def cancel_request(self, request: ServiceRequest) -> None:
        if request.technician:
            request.technician.is_available = True
        request.status = RequestStatus.CANCELLED
        self._log(f"{request.ticket_no()} cancelled")

    def list_requests(self, status: Optional[RequestStatus] = None) -> List[ServiceRequest]:
        requests = list(self._requests.values())
        if status:
            requests = [r for r in requests if r.status == status]
        return requests

    # ---------------- Overview / analytics module ----------------

    def stats(self) -> dict:
        active_statuses = {RequestStatus.ASSIGNED, RequestStatus.IN_PROGRESS}
        return {
            "technicians": len(self._technicians),
            "available_now": sum(1 for t in self._technicians.values() if t.is_available),
            "active_jobs": sum(1 for r in self._requests.values() if r.status in active_statuses),
            "completed": sum(1 for r in self._requests.values() if r.status == RequestStatus.COMPLETED),
        }

    def requests_by_category(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for r in self._requests.values():
            counts[r.category.value] = counts.get(r.category.value, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: -kv[1]))

    def recent_activity(self) -> List[ActivityLogEntry]:
        return list(self._activity)

    def print_overview(self) -> None:
        s = self.stats()
        print("\n=== OVERVIEW ===")
        print(f"Technicians: {s['technicians']}   Available now: {s['available_now']}   "
              f"Active jobs: {s['active_jobs']}   Completed: {s['completed']}")

        by_cat = self.requests_by_category()
        if by_cat:
            print("\nRequests by category:")
            max_count = max(by_cat.values())
            for cat, n in by_cat.items():
                bar = "#" * int(n / max_count * 20)
                print(f"  {cat:<18} {bar:<20} {n}")

        if self._activity:
            print("\nRecent activity:")
            for entry in self._activity:
                print(f"  {entry.timestamp.strftime('%H:%M:%S')}  {entry.text}")
        print()

    def print_technicians(self) -> None:
        print("\n=== TECHNICIANS ===")
        if not self._technicians:
            print("  No technicians yet.")
        for t in self._technicians.values():
            status = "Available" if t.is_available else "On a job"
            skills = ", ".join(s.value for s in t.skills)
            print(f"  #{t.technician_id} {t.name:<15} {t.location:<12} "
                  f"[{skills}]  ★{t.rating}  {status}  jobs_done={t.jobs_completed}")
        print()

    def print_requests(self) -> None:
        print("\n=== REQUESTS ===")
        if not self._requests:
            print("  No requests yet.")
        for r in self._requests.values():
            print("  " + r.summary())
        print()


# ---------------------------------------------------------------------------
# Interactive CLI (mirrors the web app's three modules)
# ---------------------------------------------------------------------------

def seed_demo_data(provider: ServiceLinkProvider):
    provider.register_technician(
        "Ravi Kumar", "9000000001", "Coimbatore",
        [ServiceCategory.PLUMBING, ServiceCategory.CLEANING], rating=4.8
    )
    provider.register_technician(
        "Suresh Babu", "9000000002", "Chennai",
        [ServiceCategory.ELECTRICAL, ServiceCategory.AC_REPAIR], rating=4.6
    )
    provider.register_technician(
        "Anitha R", "9000000003", "Coimbatore",
        [ServiceCategory.AC_REPAIR, ServiceCategory.APPLIANCE_REPAIR], rating=4.9
    )


def choose_category() -> ServiceCategory:
    cats = list(ServiceCategory)
    for i, c in enumerate(cats, 1):
        print(f"  {i}. {c.value}")
    idx = int(input("Choose category number: ")) - 1
    return cats[idx]


def run_cli():
    provider = ServiceLinkProvider()
    seed_demo_data(provider)

    menu = """
FIELDLINK DISPATCH CONSOLE
  1) Overview
  2) Technicians -> list
  3) Technicians -> add
  4) Requests -> list
  5) Requests -> new (auto-links to best technician)
  6) Requests -> start work
  7) Requests -> complete
  8) Requests -> cancel
  0) Exit
"""
    while True:
        print(menu)
        choice = input("Select option: ").strip()

        if choice == "1":
            provider.print_overview()

        elif choice == "2":
            provider.print_technicians()

        elif choice == "3":
            name = input("Technician name: ")
            location = input("Location: ")
            print("Select skills (comma-separated numbers):")
            cats = list(ServiceCategory)
            for i, c in enumerate(cats, 1):
                print(f"  {i}. {c.value}")
            raw = input("Skills: ")
            skills = [cats[int(i.strip()) - 1] for i in raw.split(",") if i.strip()]
            provider.register_technician(name, "N/A", location, skills)
            print("Technician added.")

        elif choice == "4":
            provider.print_requests()

        elif choice == "5":
            cust_name = input("Customer name: ")
            cust_loc = input("Customer location: ")
            customer = provider.register_customer(cust_name, "N/A", cust_loc)
            category = choose_category()
            desc = input("Description: ")
            request = provider.create_request(customer, category, desc)
            linked = provider.link(request)
            print("Linked!" if linked else "No technician available yet.")
            print("  " + request.summary())

        elif choice == "6":
            rid = int(input("Request ID: "))
            provider.start_work(provider._requests[rid])
            print("Work started.")

        elif choice == "7":
            rid = int(input("Request ID: "))
            provider.complete_request(provider._requests[rid])
            print("Marked complete.")

        elif choice == "8":
            rid = int(input("Request ID: "))
            provider.cancel_request(provider._requests[rid])
            print("Cancelled.")

        elif choice == "0":
            print("Goodbye.")
            break

        else:
            print("Invalid option.")


if __name__ == "__main__":
    run_cli()