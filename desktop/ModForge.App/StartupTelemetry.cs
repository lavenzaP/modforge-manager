using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Text;

namespace ModForge.App
{
    public sealed class StartupTelemetry
    {
        private readonly Stopwatch stopwatch;
        private readonly List<string> events;

        public StartupTelemetry()
        {
            stopwatch = Stopwatch.StartNew();
            events = new List<string>();
        }

        public long ElapsedMilliseconds
        {
            get { return stopwatch.ElapsedMilliseconds; }
        }

        public void Mark(string name)
        {
            events.Add(string.Format("{0}ms {1}", stopwatch.ElapsedMilliseconds, name));
        }

        public string Summary()
        {
            var builder = new StringBuilder();
            builder.AppendFormat("Window ready in {0}ms. Python sidecar: not probed at startup.", stopwatch.ElapsedMilliseconds);

            if (events.Count > 0)
            {
                builder.Append(" Events: ");
                builder.Append(string.Join(" | ", events.ToArray()));
            }

            return builder.ToString();
        }
    }
}
