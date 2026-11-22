// 來源：E:/test_python3/PythonToUnityReceiver.cs 的有效版本。
// 保留 TCP + ReadLine + JSON + 座標縮放 + Unity Update 移動物件的架構。
// 整理修正：斷線可重接、停止時關閉 client、只保留最新座標，避免排隊延遲。
// 左右手可各自指定物件；沒有指定時，沿用原本移動掛載物件的行為。
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
    public float coordinateDivisor = 100f; // 沿用原始比例；不是毫米轉公尺的固定換算。
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
        // 在主執行緒建立 listener，背景執行緒只負責接收資料。
        try
        {
            server = new TcpListener(IPAddress.Any, listenPort);
            server.Start();
            isRunning = true;
            serverThread = new Thread(StartListening) { IsBackground = true };
            serverThread.Start();
            Debug.Log("Unity 等待 Python 連線，TCP port: " + listenPort);
        }
        catch (Exception error)
        {
            server?.Stop();
            Debug.LogError("Unity 無法啟動 TCP：" + error.Message);
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
                            // Python 每個 JSON 都附加換行，避免 TCP 分包或黏包。
                            string json = reader.ReadLine();
                            if (json == null) break; // EOF：回到外層，接受下一次連線。
                            if (string.IsNullOrWhiteSpace(json)) continue;
                            try
                            {
                                JObject data = JObject.Parse(json);
                                // 原始 sender 也能發送 SceneA 指令，但沒有提供場景與處理器。
                                // 目前僅處理追蹤封包，避免 command 被誤當成座標而報錯。
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
                                lock (stateLock) pendingError = "JSON 解析錯誤：" + error.Message;
                            }
                        }
                    }
                }
            }
            catch (Exception error)
            {
                if (isRunning)
                    lock (stateLock) pendingError = "Python 連線中斷，等待重連：" + error.Message;
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
                // 雙手模式只更新有指定的那隻，避免另一手覆蓋同一個物件。
                if (leftHandObject != null || rightHandObject != null) continue;
                target = leapHandObject != null ? leapHandObject.transform : transform;
            }
            Vector3 raw = pair.Value / coordinateDivisor;
            raw.z = -raw.z; // 沿用原始 Z 軸轉換。
            Vector3 next = Vector3.Lerp(target.position, raw + positionOffset, smoothing);
            next.y = Mathf.Max(next.y, 0.1f);
            target.position = next;
        }
    }

    void StopServer()
    {
        if (!isRunning) return;
        isRunning = false;
        // 只停止 listener 無法中斷 client.ReadLine，必須同時關閉 client。
        lock (stateLock) activeClient?.Close();
        server?.Stop();
        serverThread?.Join(500);
    }

    void OnApplicationQuit() { StopServer(); }
    void OnDestroy() { StopServer(); }
}
