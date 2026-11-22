// Source: Active version of E:/test_python3/PythonToUnityReceiver.cs.
// Preserves the TCP + ReadLine + JSON + coordinate scaling + Unity Update object movement architecture.
// Organization fixes: supports reconnection on disconnect, closes client on stop, and keeps only the latest coordinates to avoid queue lag.
// Allows assigning separate objects for left and right hands; when unassigned, falls back to the original behavior of moving the attached object.
using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using Newtonsoft.Json.Linq;
using UnityEngine;

public class PythonToUnityReceiver : MonoBehaviour
{
    public int listenPort = 8054;
    public GameObject leapHandObject;
    public Transform leftHandObject;
    public Transform rightHandObject;
    public Vector3 positionOffset = new Vector3(0.075f, 1.0f, 2.25f);
    public float coordinateDivisor = 100f; // Retains the original scale; not a fixed millimeter-to-meter conversion.
    [Range(0f, 1f)] public float smoothing = 0.1f;

    private TcpListener server;
    private TcpClient activeClient;
    private Thread serverThread;
    private volatile bool isRunning;
    private readonly object stateLock = new object();
    private readonly Dictionary<string, Vector3> latestPositions = new Dictionary<string, Vector3>();
    private string pendingError;

    void Start()
    {
        if (listenPort < 1 || listenPort > 65535 || coordinateDivisor <= 0f)
        {
            Debug.LogError("請檢查 TCP port 與 coordinateDivisor。");
            enabled = false;
            return;
        }
        // Create the listener on the main thread; the background thread is only responsible for receiving data.
        try
        {
            server = new TcpListener(IPAddress.Any, listenPort);
            server.Start();
            isRunning = true;
            serverThread = new Thread(StartListening) { IsBackground = true };
            serverThread.Start();
            Debug.Log("Unity waiting for Python connection，TCP port: " + listenPort);
        }
        catch (Exception error)
        {
            server?.Stop();
            Debug.LogError("Unity failed to start TCP：" + error.Message);
            enabled = false;
        }
    }

    void StartListening()
    {
        while (isRunning)
        {
            try
            {
                using (TcpClient client = server.AcceptTcpClient())
                {
                    lock (stateLock)
                    {
                        if (!isRunning) break;
                        activeClient = client;
                    }
                    using (NetworkStream stream = client.GetStream())
                    using (StreamReader reader = new StreamReader(stream, Encoding.UTF8))
                    {
                        while (isRunning)
                        {
                            // Python appends a newline to each JSON message to avoid TCP fragmentation or packet coalescing.
                            string json = reader.ReadLine();
                            if (json == null) break; // EOF: return to the outer loop to accept the next connection.
                            if (string.IsNullOrWhiteSpace(json)) continue;
                            try
                            {
                                JObject data = JObject.Parse(json);
                                // The original sender can also send SceneA commands, but no scene or handler was provided.
                                // Currently only tracking packets are processed so command packets are not misread as coordinates and cause an error.
                                if ((string)data["type"] == "command") continue;
                                JArray position = data["position"] as JArray;
                                string handType = ((string)data["hand_type"] ?? "").ToLowerInvariant();
                                if (position == null || position.Count != 3) continue;
                                string side;
                                if (handType == "left" || handType == "handtype.left") side = "left";
                                else if (handType == "right" || handType == "handtype.right") side = "right";
                                else continue;
                                float x = position[0].ToObject<float>();
                                float y = position[1].ToObject<float>();
                                float z = position[2].ToObject<float>();
                                if (float.IsNaN(x) || float.IsNaN(y) || float.IsNaN(z) ||
                                    float.IsInfinity(x) || float.IsInfinity(y) || float.IsInfinity(z)) continue;
                                lock (stateLock) latestPositions[side] = new Vector3(x, y, z);
                            }
                            catch (Exception error)
                            {
                                lock (stateLock) pendingError = "JSON parse error：" + error.Message;
                            }
                        }
                    }
                }
            }
            catch (Exception error)
            {
                if (isRunning)
                    lock (stateLock) pendingError = "Python connection lost, waiting to reconnect：" + error.Message;
            }
            finally
            {
                lock (stateLock) activeClient = null;
            }
        }
    }

    void Update()
    {
        Dictionary<string, Vector3> positions;
        string error;
        lock (stateLock)
        {
            positions = new Dictionary<string, Vector3>(latestPositions);
            error = pendingError;
            pendingError = null;
        }
        if (error != null) Debug.LogWarning(error);
        foreach (KeyValuePair<string, Vector3> pair in positions)
        {
            Transform target = pair.Key == "left" ? leftHandObject : rightHandObject;
            if (target == null)
            {
                // In two-hand mode, only update the assigned hand so the other hand does not overwrite the same object.
                if (leftHandObject != null || rightHandObject != null) continue;
                target = leapHandObject != null ? leapHandObject.transform : transform;
            }
            Vector3 raw = pair.Value / coordinateDivisor;
            raw.z = -raw.z; // Retains the original Z-axis conversion.
            Vector3 next = Vector3.Lerp(target.position, raw + positionOffset, smoothing);
            next.y = Mathf.Max(next.y, 0.1f);
            target.position = next;
        }
    }

    void StopServer()
    {
        if (!isRunning) return;
        isRunning = false;
        // Stopping the listener alone cannot interrupt client.ReadLine; the client must be closed as well.
        lock (stateLock) activeClient?.Close();
        server?.Stop();
        serverThread?.Join(500);
    }

    void OnApplicationQuit() { StopServer(); }
    void OnDestroy() { StopServer(); }
}
