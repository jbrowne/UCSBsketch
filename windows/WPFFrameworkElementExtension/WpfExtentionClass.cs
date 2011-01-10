using System;
using Microsoft.Scripting.Runtime;
using System.Windows;
using System.Runtime.CompilerServices;

//http://blogs.msdn.com/srivatsn/archive/2008/04/12/turning-your-net-object-models-dynamic-for-ironpython.aspx

//This is the 'magic' line which implements the extensionMethods on the WPF's base class, FrameworkElements
[assembly: ExtensionType(typeof(FrameworkElement), typeof(WPFFrameworkElementExtension.WpfExtentionClass))]

namespace WPFFrameworkElementExtension
{
    public class WpfExtentionClass
    {

        /*
         * Make this function get treated a special way.  GetBoundMember is when things are looked up by the CLR, 
         * and checked AFTER the normal .NET Lookups.  So we can, (from within a dynamic language), do
         * someWpfElement.NamedItem.
         * */
        [SpecialName]   
        public static object GetBoundMember(FrameworkElement e, string n)
        {
            //Search through the WpfElement's objects
            object result = e.FindName(n);

            if (result == null)
            {
                return OperationFailed.Value;
            }

            return result;

            //If we wanted to add The dynamic Python-type support for adding/removing things to the CLR Classes, we can create a Dict and return the pertinent stuff
            //And also create a SpecialName SetMemberAfter method.
        }  
    }
}
