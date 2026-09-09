using System;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading;

public static class FakeAgy
{
    public static int Main(string[] args)
    {
        if (args.Contains("--version")) { Console.WriteLine("9.9.9-test"); return 0; }
        if (args.Contains("--help"))
        {
            Console.WriteLine("--mode Set mode (accept-edits, plan)");
            Console.WriteLine("--print Run prompt");
            Console.WriteLine("--prompt-interactive Interactive prompt");
            Console.WriteLine("--dangerously-skip-permissions Auto approve");
            Console.WriteLine("--sandbox Sandbox");
            return 0;
        }
        if (args.Contains("agent") || args.Contains("agents")) { return 0; }
        var promptArgument = args.FirstOrDefault(value => value.StartsWith("--print=")) ?? "";
        var prompt = promptArgument.StartsWith("--print=") ? promptArgument.Substring(8) : promptArgument;
        var logIndex = Array.IndexOf(args, "--log-file");
        if (logIndex >= 0 && logIndex + 1 < args.Length)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(args[logIndex + 1]));
            File.WriteAllText(args[logIndex + 1], "fake execution log");
        }
        var sleepMatch = Regex.Match(prompt, @"SLEEP:(\d+)");
        int milliseconds;
        if (sleepMatch.Success && Int32.TryParse(sleepMatch.Groups[1].Value, out milliseconds)) { Thread.Sleep(milliseconds); }
        var failMatch = Regex.Match(prompt, @"FAIL_ONCE:(\S+)");
        if (failMatch.Success)
        {
            var marker = failMatch.Groups[1].Value;
            if (!File.Exists(marker)) { File.WriteAllText(marker, "failed"); Console.Error.WriteLine("intentional first failure"); return 7; }
        }
        var outputMatch = Regex.Match(prompt, @"OUTPUT_BYTES:(\d+)");
        int outputBytes;
        if (outputMatch.Success && Int32.TryParse(outputMatch.Groups[1].Value, out outputBytes))
        {
            Console.Write(new string('x', outputBytes));
            return 0;
        }
        Console.WriteLine("status: COMPLETE");
        Console.WriteLine(prompt);
        return 0;
    }
}
