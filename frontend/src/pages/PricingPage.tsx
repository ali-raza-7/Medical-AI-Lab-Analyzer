import { ArrowLeft, Check } from "lucide-react";
import { Link } from "react-router-dom";

const PLANS = [
  {
    name: "Basic",
    price: 6,
    duration: "1 Year",
    credits: 100,
    badge: null,
    features: [
      "100 Lab Report Analyses",
      "AI Clinical Interpretation",
      "PDF & Image Support",
      "History & Comparison",
      "Email Support",
    ],
  },
  {
    name: "Popular",
    price: 12,
    duration: "2 Years",
    credits: 250,
    popular: true,
    features: [
      "250 Lab Report Analyses",
      "AI Clinical Interpretation",
      "PDF & Image Support",
      "History & Comparison",
      "Priority Support",
      "Advanced Biomarker Charts",
    ],
  },
  {
    name: "Pro",
    price: 16,
    duration: "3 Years",
    credits: 600,
    badge: null,
    features: [
      "600 Lab Report Analyses",
      "AI Clinical Interpretation",
      "PDF & Image Support",
      "History & Comparison",
      "Priority Support",
      "Advanced Biomarker Charts",
      "Early Access to New Features",
    ],
  },
];

function PricingPage() {
  const handleClick = () => {
    alert("Payment integration coming soon! Contact support@labsystem.com");
  };

  return (
    <div className="space-y-6 pb-12 animate-in fade-in duration-500">
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-emerald-500 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Dashboard
      </Link>

      <div className="text-center space-y-4 mb-10">
        <span className="inline-block text-[10px] font-bold uppercase tracking-widest text-emerald-500 bg-emerald-500/10 px-3 py-1 rounded-full">
          Pricing
        </span>
        <h1 className="text-4xl font-bold tracking-tight text-white">
          Choose Your Plan
        </h1>
        <p className="text-sm text-slate-400 max-w-md mx-auto">
          Unlock unlimited medical report analysis
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-3 items-center max-w-5xl mx-auto">
        {PLANS.map((plan) => (
          <div
            key={plan.name}
            className={`relative rounded-2xl transition-all duration-300 flex flex-col border border-slate-700 hover:border-emerald-500 hover:shadow-lg hover:shadow-emerald-500/20 p-8 ${
              plan.popular ? "bg-slate-900" : "bg-slate-900/80"
            }`}>
            <div className="space-y-2">
              <h3 className="text-lg font-bold text-white">{plan.name}</h3>
              <div className="flex items-baseline gap-1">
                <span className="text-5xl font-bold text-white">${plan.price}</span>
              </div>
              <p className="text-sm text-slate-400">{plan.duration} &middot; {plan.credits} credits</p>
            </div>

            <div className="my-6 h-px bg-slate-800" />

            <ul className="space-y-3 flex-1">
              {plan.features.map((f) => (
                <li key={f} className="flex items-start gap-3 text-sm text-slate-300">
                  <Check className="h-4 w-4 mt-0.5 text-emerald-500 flex-shrink-0" />
                  {f}
                </li>
              ))}
            </ul>

            <button
              onClick={handleClick}
              className="mt-8 w-full py-3 rounded-xl font-bold text-sm transition-all bg-slate-800 text-slate-200 hover:bg-emerald-500 hover:text-white"
            >
              Get Started
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default PricingPage;
