import React, { useEffect, useState } from 'react';
import { SecureAPI } from '../lib/secureApi';

interface ReservationDetail {
    id: string;
    check_in: string;
    check_out: string;
    amount: string;
    currency: string;
}

interface RevenueData {
    property_id: string;
    month: number;
    year: number;
    timezone: string;
    total_revenue: string;
    currency: string;
    reservations_count: number;
    reservations: ReservationDetail[];
}

interface RevenueSummaryProps {
    propertyId?: string;
    month?: number;
    year?: number;
    debugTenant?: string;
    showRaw?: boolean;
}

const MONTH_NAMES = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
];

const formatAmount = (value: string, currency: string) =>
    `${currency} ${new Intl.NumberFormat(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    }).format(Number(value))}`;

const formatDate = (iso: string, timeZone?: string) => {
    try {
        const d = new Date(iso);
        return d.toLocaleString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            timeZone,
        });
    } catch {
        return iso;
    }
};

export const RevenueSummary: React.FC<RevenueSummaryProps> = ({
    propertyId = 'prop-001',
    month = 3,
    year = 2026,
    debugTenant,
    showRaw,
}) => {
    const [data, setData] = useState<RevenueData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [expanded, setExpanded] = useState(false);

    const activeTenant = debugTenant || 'candidate';

    useEffect(() => {
        const fetchRevenue = async () => {
            setLoading(true);
            setError('');
            try {
                const response = await SecureAPI.getDashboardSummary(propertyId, {
                    simulatedTenant: activeTenant,
                    timestamp: Date.now(),
                    month,
                    year,
                });
                setData(response);
            } catch (err) {
                setError('Failed to load revenue data');
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        fetchRevenue();
    }, [propertyId, activeTenant, month, year]);

    if (loading) {
        return (
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
                <div className="animate-pulse space-y-4">
                    <div className="h-4 bg-gray-100 rounded w-1/4"></div>
                    <div className="h-8 bg-gray-100 rounded w-1/2"></div>
                    <div className="flex gap-4 pt-4">
                        <div className="h-12 bg-gray-100 rounded flex-1"></div>
                        <div className="h-12 bg-gray-100 rounded flex-1"></div>
                    </div>
                </div>
            </div>
        );
    }

    if (error) return <div className="p-4 text-red-500 bg-red-50 rounded-lg">{error}</div>;
    if (!data) return null;

    const monthLabel = `${MONTH_NAMES[data.month - 1]} ${data.year}`;
    const hasData = data.reservations_count > 0;

    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow duration-300">
            {showRaw && (
                <div className="p-3 bg-gray-50 text-xs font-mono border-b border-gray-100 overflow-auto max-h-32">
                    <strong className="block mb-1 text-gray-500 uppercase tracking-wider text-[10px]">Raw API Response</strong>
                    <pre className="text-gray-700">{JSON.stringify(data, null, 2)}</pre>
                </div>
            )}

            <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                    <div className="w-full">
                        <div className="flex items-center gap-2">
                            <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide">Total Revenue</h2>
                            <span className="text-[11px] font-semibold uppercase tracking-wider text-blue-700 bg-blue-50 px-2 py-0.5 rounded">
                                {monthLabel}
                            </span>
                            <span className="text-[11px] text-gray-400">· tz {data.timezone}</span>
                        </div>

                        {hasData ? (
                            <div className="flex items-baseline gap-2 mt-1">
                                <span className="text-3xl font-bold text-gray-900 tracking-tight">
                                    {formatAmount(data.total_revenue, data.currency)}
                                </span>
                            </div>
                        ) : (
                            <div className="mt-2 text-sm text-gray-500 italic">
                                No data for {monthLabel}.
                            </div>
                        )}
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-100">
                    <div>
                        <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">Property ID</p>
                        <p className="text-sm font-semibold text-gray-700 font-mono mt-1">{data.property_id}</p>
                    </div>
                    <div>
                        <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">Reservations</p>
                        {hasData ? (
                            <button
                                type="button"
                                onClick={() => setExpanded((v) => !v)}
                                className="mt-1 flex items-center gap-1.5 text-sm font-semibold text-gray-700 hover:text-gray-900 focus:outline-none"
                                aria-expanded={expanded}
                            >
                                <span>
                                    {data.reservations_count}{' '}
                                    <span className="font-normal text-gray-400">bookings</span>
                                </span>
                                <svg
                                    className={`h-4 w-4 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                >
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                            </button>
                        ) : (
                            <p className="text-sm font-semibold text-gray-700 mt-1">
                                0 <span className="font-normal text-gray-400">bookings</span>
                            </p>
                        )}
                    </div>
                </div>

                {hasData && (
                    <div
                        className={`grid transition-[grid-template-rows] duration-300 ease-out ${
                            expanded ? 'grid-rows-[1fr] mt-4' : 'grid-rows-[0fr] mt-0'
                        }`}
                    >
                        <div className="overflow-hidden">
                            <div
                                className={`border-t border-gray-100 pt-4 space-y-2 transition-opacity duration-300 ${
                                    expanded ? 'opacity-100' : 'opacity-0'
                                }`}
                            >
                                {data.reservations.map((r, i) => (
                                    <div
                                        key={r.id}
                                        style={{ transitionDelay: expanded ? `${i * 40}ms` : '0ms' }}
                                        className={`flex items-center justify-between text-xs bg-gray-50 rounded px-3 py-2 transform transition-all duration-300 ease-out ${
                                            expanded
                                                ? 'opacity-100 translate-y-0'
                                                : 'opacity-0 -translate-y-1'
                                        }`}
                                    >
                                        <div className="flex flex-col">
                                            <span className="font-mono text-gray-600">{r.id}</span>
                                            <span className="text-gray-500">
                                                {formatDate(r.check_in, data.timezone)} → {formatDate(r.check_out, data.timezone)}
                                            </span>
                                        </div>
                                        <span className="font-semibold text-gray-800">
                                            {formatAmount(r.amount, r.currency)}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
