// Execute the pinned upstream maintenance model with Node's virtual clock.
// Database writes, list broadcasts and cache invalidation are isolated stubs.
// Cron generation, timezone handling, status and duration timers are upstream code.
const assert = require('node:assert/strict');
const path = require('node:path');
const { createRequire } = require('node:module');
const { mock } = require('node:test');
const source = path.resolve(process.argv[2]);
const upstream = createRequire(path.join(source, 'package.json'));
assert.equal(upstream('./package.json').version, '2.5.9');
const dayjs = upstream('dayjs');
dayjs.extend(upstream('dayjs/plugin/utc'));
dayjs.extend(upstream('./server/modules/dayjs/plugin/timezone'));
dayjs.extend(upstream('dayjs/plugin/customParseFormat'));
const fakeServer = { sendMaintenanceListByUserID() {}, async getTimezone() { return 'UTC'; } };
require.cache[upstream.resolve('./server/uptime-kuma-server')] = {
    exports: { UptimeKumaServer: { getInstance: () => fakeServer } }
};
require.cache[upstream.resolve('./server/utils/response-cache')] = { exports: { clear() {} } };
upstream('redbean-node').R.store = async () => 1;
const Maintenance = upstream('./server/model/maintenance');

async function flush() { for (let i = 0; i < 20; i++) await Promise.resolve(); }

async function scenario(label, now, start, end, expected, next) {
    mock.timers.enable({ apis: ['Date', 'setTimeout'], now: Date.parse(now) });
    const bean = Object.assign(Object.create(Maintenance.prototype), { beanMeta: {}, id: 1, user_id: 1 });
    try {
        const slot = value => ({ hours: Number(value.slice(0, 2)), minutes: Number(value.slice(3)) });
        await Maintenance.jsonToBean(bean, {
            title: 'KumaOps DST verification', description: '', strategy: 'recurring-weekday',
            intervalDay: 1, active: true, timezoneOption: 'Europe/London',
            dateRange: ['2026-01-01 00:00:00'], timeRange: [slot(start), slot(end)],
            weekdays: [0], daysOfMonth: []
        });
        await bean.run(true);
        assert.equal(bean.beanMeta.job.nextRun().toISOString(), expected, label + ': next UTC start');
        if (next) {
            assert.equal(bean.beanMeta.job.nextRun(new Date(expected)).toISOString(), next,
                label + ': next week preserves local time');
        }
        mock.timers.tick(Date.parse(expected) - Date.parse(now));
        await flush();
        assert.equal(await bean.getStatus(), 'under-maintenance', label + ': enters maintenance');
        mock.timers.tick(bean.duration * 1000);
        await flush();
        assert.equal(await bean.getStatus(), 'scheduled', label + ': ends after configured duration');
        console.log('PASS ' + label);
    } finally {
        bean.stop();
        mock.timers.reset();
    }
}

(async () => {
    await scenario('spring local 03:00', '2026-03-22T02:59:59Z', '03:00', '03:30',
        '2026-03-22T03:00:00.000Z', '2026-03-29T02:00:00.000Z');
    await scenario('autumn local 03:00', '2026-10-18T01:59:59Z', '03:00', '03:30',
        '2026-10-18T02:00:00.000Z', '2026-10-25T03:00:00.000Z');
    await scenario('nonexistent spring 01:30', '2026-03-29T00:59:59Z', '01:30', '02:00',
        '2026-03-29T01:30:00.000Z');
    await scenario('ambiguous autumn 01:30', '2026-10-25T00:29:59Z', '01:30', '02:00',
        '2026-10-25T01:30:00.000Z', '2026-11-01T01:30:00.000Z');
})().catch(error => { console.error(error.message); process.exitCode = 1; });
