import { User } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";

interface PatientMetadataCardProps {
  age: number;
  gender: string;
  setAge: (age: number) => void;
  setGender: (gender: string) => void;
  setManualAgeOverride: (val: boolean) => void;
  setManualGenderOverride: (val: boolean) => void;
}

export function PatientMetadataCard({
  age,
  gender,
  setAge,
  setGender,
  setManualAgeOverride,
  setManualGenderOverride,
}: PatientMetadataCardProps) {
  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-center gap-2">
          <User className="h-4 w-4 text-[#14b8a6]" aria-hidden="true" />
          <CardTitle className="text-xs font-bold uppercase tracking-widest text-slate-500 dark:text-[#94a3b8]">
            Patient Metadata
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 pt-0">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label htmlFor="patient-age" className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-[#64748b]">
              Age (Years)
            </label>
            <input
              id="patient-age"
              type="number"
              value={age}
              onChange={(e) => {
                setManualAgeOverride(true);
                setAge(parseInt(e.target.value) || 0);
              }}
              className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 outline-none transition focus:border-[#14b8a6] focus:ring-1 focus:ring-[#14b8a6]/20 dark:border-[#1e293b] dark:bg-[#020617] dark:text-white"
              aria-label="Patient age in years"
              min={0}
              max={150}
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="patient-gender" className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-[#64748b]">
              Gender
            </label>
            <select
              id="patient-gender"
              value={gender}
              onChange={(e) => {
                setManualGenderOverride(true);
                setGender(e.target.value);
              }}
              className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 outline-none transition focus:border-[#14b8a6] focus:ring-1 focus:ring-[#14b8a6]/20 dark:border-[#1e293b] dark:bg-[#020617] dark:text-white"
              aria-label="Patient gender"
            >
              <option value="male">Male</option>
              <option value="female">Female</option>
            </select>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
