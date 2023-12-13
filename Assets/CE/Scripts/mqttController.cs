using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class mqttController : MonoBehaviour
{
    //public Transform LeftArm;
    public Transform model;
    //public Transform Hips;
    /*
    public Transform Spine;
    public Transform Spine1;
    public Transform Spine2;
    public Transform LeftShoulder;
    */
    public string nameController = "Controller 1";
    public string tagOfTheMQTTReceiver = "datareceiver";
    public mqttReceiver _eventSender;

    void Start()
    {
        model.localRotation = Quaternion.Euler(0F, 0F, 0F);
        //float moveArmXPosition = newMsg * 30;
        //model.localRotation = Quaternion.Euler(30F, 0F, 0F);
        //model.localPosition = new Vector3(5F, 5F, 5F);
        //float leftArmRotation = 23.0F;
        //model.Hips.Spine.Spine1.Spine2.LeftShoulder.LeftArm.localRotation = Quaternion.Euler(leftArmRotation, leftArmRotation, leftArmRotation);
        _eventSender =GameObject.FindGameObjectsWithTag(tagOfTheMQTTReceiver)[0].gameObject.GetComponent<mqttReceiver>();
        _eventSender.OnMessageArrived += OnMessageArrivedHandler;
    }

    private void OnMessageArrivedHandler(string newMsg)
    {
        float toParse = float.Parse(newMsg);
        float moveArmXPosition = toParse * -40;
        model.localRotation = Quaternion.Euler(moveArmXPosition, 0F, 0F);
        //LeftArm.localRotation = Quaternion.Euler(leftArmRotation,leftArmRotation,leftArmRotation);
        Debug.Log("Event Fired. The message, from Object " +nameController+" is = " + newMsg);
    }

    private void Update()
    {
        float leftArmRotation = 23.0F;
        //LeftArm.localRotation = Quaternion.Euler(leftArmRotation, leftArmRotation, leftArmRotation);
    }
}
